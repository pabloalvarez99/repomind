r"""Rebuild the credential-free UI evidence in ``docs/assets``.

Run ``pip install -e \".[docs]\" && playwright install chromium`` once, then
``python scripts/capture_ui.py``. The script starts the packaged FastAPI app on a
dedicated port, drives the real ``GET /ask`` console over the committed fixture and
snapshot catalogs, and asserts the rendered outcome before every screenshot. It never
reads provider keys and never leaves the local process.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
HOST = "127.0.0.1"
PORT = 8021
BASE_URL = f"http://{HOST}:{PORT}"
VIEWPORT = {"width": 1280, "height": 900}
STABLE_REQUEST_ID = "capture-fixed-request-id"


@dataclass(frozen=True)
class Capture:
    """One deterministic console screenshot and the outcome it must show."""

    name: str
    repo_id: str
    question: str
    outcome: str

    @property
    def path(self) -> Path:
        """Return the PNG destination for this capture."""
        return ASSETS / f"{self.name}.png"

    @property
    def url(self) -> str:
        """Return the console URL that renders this capture."""
        query = urllib.parse.urlencode({"question": self.question, "repo_id": self.repo_id})
        return f"{BASE_URL}/ask?{query}"


CAPTURES = (
    Capture(
        name="ui-mini-hit",
        repo_id="mini",
        question="Where is create_app defined?",
        outcome="found",
    ),
    Capture(
        name="ui-mini-refuse",
        repo_id="mini",
        question="Where is QuantumDatabaseRouter defined?",
        outcome="refused",
    ),
    Capture(
        name="ui-dogfood-hit",
        repo_id="production_rag",
        question="Where is reciprocal_rank_fusion defined?",
        outcome="found",
    ),
)


def _port_is_free() -> bool:
    """Report whether the capture port can be bound right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((HOST, PORT)) != 0


def _wait_for_api(process: subprocess.Popen[bytes], timeout: float = 60.0) -> None:
    """Block until the local app answers ``/health``.

    Raises:
        RuntimeError: The server exited or never became healthy.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    raise RuntimeError(f"API did not become healthy within {timeout:.0f} seconds")


def _stabilize_request_id(page: Page) -> None:
    """Freeze the per-request correlation id without hiding the field itself."""
    page.locator(".request-id code").evaluate(
        "(node, value) => { node.textContent = value; }", STABLE_REQUEST_ID
    )


def _render(page: Page, capture: Capture) -> None:
    """Load one console URL and assert the outcome the capture claims.

    Raises:
        RuntimeError: The console rendered citations that contradict the outcome.
    """
    page.goto(capture.url, wait_until="networkidle")
    page.locator(f".status.{capture.outcome}").wait_for(state="visible")
    citations = page.locator(".citations .location").count()
    if capture.outcome == "found" and citations == 0:
        raise RuntimeError(f"{capture.name}: expected at least one path:line citation")
    if capture.outcome == "refused" and citations != 0:
        raise RuntimeError(f"{capture.name}: refusal must render zero citations")
    _stabilize_request_id(page)
    page.screenshot(path=capture.path, full_page=True, animations="disabled", caret="hide")


def _print_hashes() -> None:
    """Print a sha256 for every capture so reviewers can diff reruns."""
    for capture in CAPTURES:
        digest = hashlib.sha256(capture.path.read_bytes()).hexdigest()
        print(f"{capture.name}: {digest}  {capture.path.relative_to(ROOT)}")


def capture_all() -> None:
    """Start the offline app and write every documented console screenshot.

    Raises:
        RuntimeError: Playwright is missing or the capture port is occupied.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Playwright is documentation-only; install it with pip install -e ".[docs]"'
        ) from exc

    if not _port_is_free():
        raise RuntimeError(f"port {PORT} is already in use; stop the other process first")

    env = os.environ.copy()
    env.pop("REPOMIND_CATALOG_PRODUCTION_RAG", None)
    ASSETS.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "repomind.main:app", "--host", HOST, "--port", str(PORT)],
        cwd=ROOT,
        env=env,
    )
    try:
        _wait_for_api(server)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
            for capture in CAPTURES:
                _render(page, capture)
            browser.close()
        _print_hashes()
    finally:
        server.terminate()
        server.wait(timeout=30)


def main() -> int:
    """Parse CLI arguments and return a process exit code."""
    parser = argparse.ArgumentParser(description="Regenerate docs/assets console screenshots.")
    parser.parse_args()
    try:
        capture_all()
    except (RuntimeError, subprocess.SubprocessError) as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

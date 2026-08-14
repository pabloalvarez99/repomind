"""Record the hashes that keep committed console evidence honest.

CI never launches a browser, so nothing regenerates ``docs/assets/*.png``. Two
sidecars stand in for that: ``ui-captures.sha256`` pins the committed screenshots,
and ``ui-sources.sha256`` pins the files that decide what a screenshot looks like.
Editing a template, the stylesheet, the console script, or the capture script
changes a source hash, and ``tests/test_capture_assets.py`` then fails until the
author reruns ``scripts/capture_ui.py`` and refreshes both sidecars here.

Run ``python scripts/hash_ui_assets.py`` after a capture run, or
``python scripts/hash_ui_assets.py --check`` to see the drift without writing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
CAPTURE_MANIFEST = ASSETS / "ui-captures.sha256"
SOURCE_MANIFEST = ASSETS / "ui-sources.sha256"

# Every file whose bytes can change the rendered console, plus the script that
# renders it. A change to any of them invalidates the committed screenshots.
SOURCE_PATHS = (
    "src/repomind/templates/index.html",
    "src/repomind/static/app.css",
    "src/repomind/static/app.js",
    "scripts/capture_ui.py",
)


def _digest(path: Path, *, text: bool) -> str:
    """Return the sha256 hex digest of one file.

    Args:
        path: File to hash.
        text: Normalize CRLF to LF first. Git checks the UI sources out with native
            line endings, so a Windows working copy would otherwise disagree with a
            Linux CI runner over bytes neither of them changed. PNGs are hashed raw.
    """
    payload = path.read_bytes()
    if text:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _render(relative_paths: list[str], *, text: bool) -> str:
    """Render sha256sum-style manifest text for repo-relative paths."""
    return "".join(
        f"{_digest(ROOT / relative, text=text)}  {relative}\n" for relative in relative_paths
    )


def capture_manifest() -> str:
    """Return the manifest text for every committed capture PNG."""
    captures = sorted(path.relative_to(ROOT).as_posix() for path in ASSETS.glob("*.png"))
    return _render(captures, text=False)


def source_manifest() -> str:
    """Return the manifest text for every file that decides the rendered console."""
    return _render(sorted(SOURCE_PATHS), text=True)


MANIFESTS = ((CAPTURE_MANIFEST, capture_manifest), (SOURCE_MANIFEST, source_manifest))


def main() -> int:
    """Write or verify both sidecars and return a process exit code."""
    parser = argparse.ArgumentParser(description="Refresh the UI evidence sha256 sidecars.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift instead of rewriting the sidecars",
    )
    arguments = parser.parse_args()

    stale = False
    for manifest, build in MANIFESTS:
        expected = build()
        current = manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
        relative = manifest.relative_to(ROOT).as_posix()
        if arguments.check:
            if current != expected:
                stale = True
                print(f"stale: {relative}", file=sys.stderr)
            continue
        if current != expected:
            manifest.write_text(expected, encoding="utf-8", newline="\n")
            print(f"updated {relative}")
        else:
            print(f"unchanged {relative}")

    if stale:
        print(
            "rerun scripts/capture_ui.py, then scripts/hash_ui_assets.py, "
            "and commit the result alongside the change that caused it",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

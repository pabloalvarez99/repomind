#!/usr/bin/env python3
"""Generate committed history snapshots for catalog fixtures.

Why this exists
---------------
The hosted free path runs on Vercel without ``git(1)`` in the image, and catalog
fixtures are not stand-alone git work trees. Shelling out to git on the request
path therefore always becomes ``503 capability_missing`` in production — a fake
History button.

This script writes a deterministic, content-addressed log/blame table under each
fixture root at ``.repomind/history.jsonl``. Runtime history reads that file and
never needs git for packaged fixtures. Re-run the script after editing fixture
bytes; the committed snapshot is the honesty contract.

Usage
-----
From the repository root (after ``pip install -e .`` is optional; only stdlib)::

    python scripts/generate_history_snapshots.py
    python scripts/generate_history_snapshots.py --check   # exit 1 if stale

Determinism
-----------
For each text file under a fixture (skipping ``.repomind/`` itself and binary
extensions), the script derives a 40-hex "sha" from the normalized path + file
bytes, a single log entry, and one blame row per non-empty line. Same bytes ⇒
same snapshot. No wall clock, no author env, no git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "fixtures"
SNAPSHOT_REL = Path(".repomind") / "history.jsonl"

# Keep in lockstep with repomind.history.SNAPSHOT_RELATIVE_PATH.
TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".html",
    ".css",
}
SKIP_DIR_NAMES = {".repomind", ".git", "__pycache__", "node_modules"}
AUTHOR = "RepoMind Snapshot"
COMMITTED_AT = "2026-01-01T00:00:00Z"
SUMMARY = "committed fixture history snapshot"


def _normalize_bytes(data: bytes) -> bytes:
    """Collapse CRLF so Windows and Linux checkouts produce one snapshot."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _file_sha(relative: str, data: bytes) -> str:
    """Return a git-shaped 40-hex id derived only from path and bytes."""
    payload = b"snapshot\0" + relative.encode("utf-8") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def _iter_fixture_files(root: Path) -> list[Path]:
    """Return sorted source-like files under ``root``, excluding snapshot dirs."""
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_NAMES for part in rel_parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        found.append(path)
    return found


def _rows_for_file(root: Path, path: Path) -> list[dict[str, object]]:
    """Build log + blame rows for one fixture file."""
    relative = path.relative_to(root).as_posix()
    data = _normalize_bytes(path.read_bytes())
    sha = _file_sha(relative, data)
    rows: list[dict[str, object]] = [
        {
            "path": relative,
            "mode": "log",
            "sha": sha,
            "summary": SUMMARY,
            "author": AUTHOR,
            "committed_at": COMMITTED_AT,
        }
    ]
    text = data.decode("utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        rows.append(
            {
                "path": relative,
                "mode": "blame",
                "sha": sha,
                "summary": SUMMARY,
                "author": AUTHOR,
                "committed_at": COMMITTED_AT,
                "line": line_no,
            }
        )
    return rows


def generate_snapshot(root: Path) -> str:
    """Return the canonical history.jsonl text for one fixture root."""
    rows: list[dict[str, object]] = []
    for path in _iter_fixture_files(root):
        rows.extend(_rows_for_file(root, path))
    lines = [json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows]
    return "\n".join(lines) + ("\n" if lines else "")


def write_fixture_snapshots(*, check: bool) -> int:
    """Write or verify snapshots for every directory under fixtures/."""
    if not FIXTURES_ROOT.is_dir():
        print(f"fixtures root missing: {FIXTURES_ROOT}", file=sys.stderr)
        return 2
    stale = 0
    for child in sorted(FIXTURES_ROOT.iterdir()):
        if not child.is_dir():
            continue
        body = generate_snapshot(child)
        target = child / SNAPSHOT_REL
        if check:
            if not target.is_file():
                print(f"MISSING {target.relative_to(REPO_ROOT)}")
                stale += 1
                continue
            current = target.read_text(encoding="utf-8")
            if current != body:
                print(f"STALE   {target.relative_to(REPO_ROOT)}")
                stale += 1
            else:
                print(f"OK      {target.relative_to(REPO_ROOT)}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8", newline="\n")
        print(f"WROTE   {target.relative_to(REPO_ROOT)} ({body.count(chr(10))} lines)")
    return 1 if stale else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: generate or check committed history snapshots."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any fixture snapshot is missing or stale",
    )
    args = parser.parse_args(argv)
    return write_fixture_snapshots(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())

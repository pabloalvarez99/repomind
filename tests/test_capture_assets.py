"""Committed UI evidence stays in sync with the docs that publish it.

Playwright is documentation-only, so CI never regenerates the PNGs. Instead these
tests hash the committed bytes against `docs/assets/ui-captures.sha256`, which the
capture script prints and the author commits alongside any template change.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
MANIFEST = ASSETS / "ui-captures.sha256"

# Documents that publish console evidence, mapped to the directory their image
# links resolve against.
DOCUMENTS = {
    ROOT / "README.md": ROOT,
    ROOT / "docs" / "SHIP.md": ROOT / "docs",
    ROOT / "docs" / "CASESTUDY.md": ROOT / "docs",
}

IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
INLINE_PATH = re.compile(r"`(docs/assets/[^`]+\.png)`")


def _manifest() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative_path = line.split("  ", maxsplit=1)
        assert relative_path not in entries, f"duplicate manifest entry {relative_path}"
        entries[relative_path] = digest
    return entries


def _referenced_pngs() -> dict[str, set[str]]:
    """Map each referenced repo-relative PNG to the documents that reference it."""
    references: dict[str, set[str]] = {}
    for document, base in DOCUMENTS.items():
        text = document.read_text(encoding="utf-8")
        targets = IMAGE_LINK.findall(text) + [
            str(ROOT / match) for match in INLINE_PATH.findall(text)
        ]
        for target in targets:
            if not target.endswith(".png"):
                continue
            resolved = Path(target) if Path(target).is_absolute() else base / target
            relative = resolved.resolve().relative_to(ROOT).as_posix()
            references.setdefault(relative, set()).add(document.name)
    return references


def test_manifest_covers_every_committed_png() -> None:
    committed = {path.relative_to(ROOT).as_posix() for path in ASSETS.glob("*.png")}
    assert committed, "docs/assets must keep the committed console evidence"
    assert set(_manifest()) == committed


def test_documented_images_exist_and_are_hashed() -> None:
    manifest = _manifest()
    references = _referenced_pngs()
    assert references, "README, SHIP, and CASESTUDY must publish console evidence"

    for relative, documents in sorted(references.items()):
        sources = ", ".join(sorted(documents))
        assert (ROOT / relative).is_file(), f"{relative} referenced by {sources} but missing"
        assert relative in manifest, (
            f"{relative} referenced by {sources} but absent from {MANIFEST.name}; "
            "rerun scripts/capture_ui.py and commit the updated hashes"
        )


def test_committed_bytes_match_the_manifest_hashes() -> None:
    for relative, digest in sorted(_manifest().items()):
        path = ROOT / relative
        assert path.is_file(), f"{relative} is hashed but not committed"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == digest, (
            f"{relative} changed without a manifest update; "
            "rerun scripts/capture_ui.py and commit the printed sha256 values"
        )


def test_every_capture_is_published_by_a_document() -> None:
    references = _referenced_pngs()
    for relative in sorted(_manifest()):
        assert relative in references, f"{relative} is committed but no document shows it"

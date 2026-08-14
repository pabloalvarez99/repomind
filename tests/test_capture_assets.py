"""Committed UI evidence stays in sync with the docs that publish it.

Playwright is documentation-only, so CI never regenerates the PNGs. Instead these
tests hash the committed bytes against `docs/assets/ui-captures.sha256`, which the
capture script prints and the author commits alongside any template change.

A second sidecar, `docs/assets/ui-sources.sha256`, hashes the template, stylesheet,
console script, and capture script. Without it a CSS or HTML edit would ship green
while the committed screenshots still showed the old console: nothing in CI can tell
that the PNGs are stale, only that they are unchanged.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import hash_ui_assets

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
MANIFEST = ASSETS / "ui-captures.sha256"
SOURCE_MANIFEST = ASSETS / "ui-sources.sha256"

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


def test_ui_sources_are_hashed_so_a_template_change_cannot_ship_stale_captures() -> None:
    recorded = SOURCE_MANIFEST.read_text(encoding="utf-8")
    assert recorded == hash_ui_assets.source_manifest(), (
        "a file that decides the rendered console changed without new evidence; "
        "rerun scripts/capture_ui.py, then scripts/hash_ui_assets.py, and commit both "
        "sidecars in the same commit as the change"
    )


def test_the_sidecar_writer_reproduces_the_committed_capture_hashes() -> None:
    # The writer and these tests must not drift apart: CONTRIBUTING tells authors to
    # run the writer, so the writer's output is what CI has to accept.
    assert MANIFEST.read_text(encoding="utf-8") == hash_ui_assets.capture_manifest()


def test_hashed_ui_sources_all_exist() -> None:
    for relative in hash_ui_assets.SOURCE_PATHS:
        assert (ROOT / relative).is_file(), f"{relative} is hashed but missing from the tree"


def test_every_capture_is_published_by_a_document() -> None:
    references = _referenced_pngs()
    for relative in sorted(_manifest()):
        assert relative in references, f"{relative} is committed but no document shows it"

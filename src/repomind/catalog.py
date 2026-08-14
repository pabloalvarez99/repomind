"""Closed repository catalog and packaged fixture locations."""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Final

MINI_REPO_ID: Final = "mini"
PRODUCTION_RAG_REPO_ID: Final = "production_rag"
PRODUCTION_RAG_CATALOG_ENV: Final = "REPOMIND_CATALOG_PRODUCTION_RAG"
REPOSITORY_IDS: Final = (MINI_REPO_ID, PRODUCTION_RAG_REPO_ID)


def _fixture_root(name: str) -> Path:
    """Return a packaged fixture root, with an editable-install fallback."""
    packaged = Path(str(files("repomind").joinpath("fixtures", name)))
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "fixtures" / name


def mini_root() -> Path:
    """Return the committed mini regression repository."""
    return _fixture_root("mini_repo")


def production_rag_snapshot_root() -> Path:
    """Return the committed read-only Production RAG snapshot."""
    return _fixture_root("production_rag")


def catalog_roots(*, allow_environment: bool = True) -> dict[str, Path]:
    """Return the closed id-to-root catalog.

    The environment may replace only the root behind the already-known
    ``production_rag`` id. It cannot add an id or turn a request value into a path.
    Evaluation callers disable this override so CI always measures committed bytes.

    Raises:
        ValueError: The optional override is not a directory.
    """
    production_root = production_rag_snapshot_root()
    override = os.environ.get(PRODUCTION_RAG_CATALOG_ENV, "").strip()
    if allow_environment and override:
        candidate = Path(override).expanduser().resolve()
        if not candidate.is_dir():
            raise ValueError(f"{PRODUCTION_RAG_CATALOG_ENV} must name a directory")
        production_root = candidate
    return {
        MINI_REPO_ID: mini_root(),
        PRODUCTION_RAG_REPO_ID: production_root,
    }

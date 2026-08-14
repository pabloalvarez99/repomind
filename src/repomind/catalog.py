"""Closed repository catalog and packaged fixture locations."""

from __future__ import annotations

import os
import re
from collections.abc import Collection
from importlib.resources import files
from pathlib import Path
from typing import Final

MINI_REPO_ID: Final = "mini"
PRODUCTION_RAG_REPO_ID: Final = "production_rag"
MINI_JS_REPO_ID: Final = "mini_js"
PRODUCTION_RAG_CATALOG_ENV: Final = "REPOMIND_CATALOG_PRODUCTION_RAG"

MAX_REPO_ID_LENGTH: Final = 64
# A catalog id is an identifier, not a slug: ``production_rag`` is a legal id and
# the underscore carries no meaning the caller may exploit. What the shape forbids
# is everything a path needs -- separators, dots, drive colons, NUL.
_WELL_FORMED_REPO_ID: Final = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class BlankRepositoryId(ValueError):
    """The caller sent no repository id at all."""


class MalformedRepositoryId(ValueError):
    """The repository id is shaped like a path or otherwise cannot name a catalog entry."""


class UnknownRepository(LookupError):
    """The caller requested a well-formed id outside the configured catalog."""


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


def mini_js_root() -> Path:
    """Return the committed mini JavaScript/TypeScript fixture."""
    return _fixture_root("mini_js")


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
        MINI_JS_REPO_ID: mini_js_root(),
    }


def catalog_ids() -> tuple[str, ...]:
    """Return the ids the catalog serves, in catalog order.

    Derived from :func:`catalog_roots` so the allowlist can never drift from the
    thing it guards. Membership does not depend on the environment: the optional
    override replaces a root, never the set of ids.
    """
    return tuple(catalog_roots(allow_environment=False))


def validate_repo_id(value: str, *, known: Collection[str] | None = None) -> str:
    """Return ``value`` when it names a catalog repository.

    This is the single validity function behind every surface -- HTTP POST, the
    browser console, the symbols route, and the CLI -- so one id cannot be legal
    on one door and rejected on the next.

    Args:
        value: Caller-supplied repository id.
        known: Allowlist to check membership against. Defaults to the catalog ids.

    Returns:
        The id, unchanged.

    Raises:
        BlankRepositoryId: ``value`` is empty or only whitespace.
        MalformedRepositoryId: ``value`` cannot be a catalog id (path-shaped, too
            long, or containing characters no id uses).
        UnknownRepository: ``value`` is well formed but is not in the catalog.
    """
    if not value or not value.strip():
        raise BlankRepositoryId("repository id must not be blank")
    if not _WELL_FORMED_REPO_ID.fullmatch(value):
        raise MalformedRepositoryId("repository id is not a catalog identifier")
    allowlist = catalog_ids() if known is None else known
    if value not in allowlist:
        raise UnknownRepository(value)
    return value

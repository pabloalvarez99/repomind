"""Closed catalog and environment override tests."""

from pathlib import Path

import pytest

from repomind.catalog import (
    MINI_REPO_ID,
    PRODUCTION_RAG_CATALOG_ENV,
    PRODUCTION_RAG_REPO_ID,
    catalog_roots,
    production_rag_snapshot_root,
)


def test_catalog_contains_only_the_two_declared_ids() -> None:
    """The public id never becomes an arbitrary filesystem selector."""
    roots = catalog_roots(allow_environment=False)

    assert tuple(roots) == (MINI_REPO_ID, PRODUCTION_RAG_REPO_ID)
    assert (roots[PRODUCTION_RAG_REPO_ID] / "NOTICE.md").is_file()


def test_local_override_replaces_only_production_rag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operators may dogfood a local root without adding a caller-controlled id."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, str(tmp_path))

    roots = catalog_roots()

    assert roots[PRODUCTION_RAG_REPO_ID] == tmp_path.resolve()
    assert roots[MINI_REPO_ID] != tmp_path.resolve()


def test_evaluation_catalog_ignores_the_environment_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI gates always use the committed snapshot, never a machine-local sibling."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, str(tmp_path))

    roots = catalog_roots(allow_environment=False)

    assert roots[PRODUCTION_RAG_REPO_ID] == production_rag_snapshot_root()


def test_invalid_override_fails_before_indexing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured but absent root is explicit instead of an empty index."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, "definitely-missing-repomind-root")

    with pytest.raises(ValueError, match=PRODUCTION_RAG_CATALOG_ENV):
        catalog_roots()

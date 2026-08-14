"""Closed catalog and environment override tests."""

from pathlib import Path

import pytest

from repomind.catalog import (
    MINI_JS_REPO_ID,
    MINI_REPO_ID,
    PRODUCTION_RAG_CATALOG_ENV,
    PRODUCTION_RAG_REPO_ID,
    BlankRepositoryId,
    MalformedRepositoryId,
    UnknownRepository,
    catalog_ids,
    catalog_roots,
    production_rag_snapshot_root,
    validate_repo_id,
)


def test_catalog_contains_only_the_declared_ids() -> None:
    """The public id never becomes an arbitrary filesystem selector."""
    roots = catalog_roots(allow_environment=False)

    assert tuple(roots) == (MINI_REPO_ID, PRODUCTION_RAG_REPO_ID, MINI_JS_REPO_ID)
    assert (roots[PRODUCTION_RAG_REPO_ID] / "NOTICE.md").is_file()
    assert (roots[MINI_JS_REPO_ID] / "src" / "foo.js").is_file()


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


def test_the_allowlist_is_derived_from_the_catalog_itself() -> None:
    """The ids callers may send are the ids the catalog can serve, not a copy."""
    assert catalog_ids() == tuple(catalog_roots(allow_environment=False))


def test_the_allowlist_does_not_move_with_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The override replaces a root; it never adds or renames an id."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, str(tmp_path))

    assert catalog_ids() == (MINI_REPO_ID, PRODUCTION_RAG_REPO_ID, MINI_JS_REPO_ID)


@pytest.mark.parametrize("repo_id", [MINI_REPO_ID, PRODUCTION_RAG_REPO_ID, MINI_JS_REPO_ID])
def test_every_catalog_id_validates(repo_id: str) -> None:
    """No published id may be unreachable through the public contract."""
    assert validate_repo_id(repo_id) == repo_id


@pytest.mark.parametrize("repo_id", ["", "   ", "\t\n"])
def test_a_missing_id_is_a_blank_id(repo_id: str) -> None:
    """Nothing sent is a schema failure, not a wrong id."""
    with pytest.raises(BlankRepositoryId):
        validate_repo_id(repo_id)


@pytest.mark.parametrize(
    "repo_id",
    [
        "..",
        "../mini",
        "mini/app",
        "mini\\app",
        "/mini",
        "C:\\mini",
        "mini\x00",
        ".hidden",
        "a" * 65,
    ],
)
def test_path_shaped_ids_are_malformed_not_merely_unknown(repo_id: str) -> None:
    """A caller reaching for the filesystem gets a different answer than a typo."""
    with pytest.raises(MalformedRepositoryId):
        validate_repo_id(repo_id)


def test_a_well_formed_id_outside_the_catalog_is_unknown() -> None:
    """A plausible typo is a 404-shaped miss, never a hint about the filesystem."""
    with pytest.raises(UnknownRepository):
        validate_repo_id("production-rag")


def test_the_underscore_id_is_not_a_slug_casualty() -> None:
    """The exact id that used to 422 on POST is valid at the one validity function."""
    assert validate_repo_id("production_rag") == "production_rag"


def test_invalid_override_fails_before_indexing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured but absent root is explicit instead of an empty index."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, "definitely-missing-repomind-root")

    with pytest.raises(ValueError, match=PRODUCTION_RAG_CATALOG_ENV):
        catalog_roots()

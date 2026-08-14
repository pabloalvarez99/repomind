"""Repository discovery tests."""

from pathlib import Path

from repomind.ingest.walk import walk_repository

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mini_repo"


def test_walk_is_sorted_and_honors_gitignore() -> None:
    """Ignored files and directories never reach ingestion."""
    paths = [item.path for item in walk_repository(FIXTURE)]

    assert paths == sorted(paths)
    assert "app/main.py" in paths
    assert "app/service.py" in paths
    assert "README.md" in paths
    assert "ignored.py" not in paths
    assert "generated/cache.py" not in paths


def test_walk_rejects_a_missing_root(tmp_path: Path) -> None:
    """A typo in the target path is explicit instead of an empty index."""
    missing = tmp_path / "missing"

    try:
        walk_repository(missing)
    except ValueError as error:
        assert "not a directory" in str(error)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("missing repository root was accepted")

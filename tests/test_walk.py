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


def test_nested_gitignore_is_relative_and_can_negate_a_parent_rule(tmp_path: Path) -> None:
    """Rules follow the directory that owns them and deeper negations win."""
    nested = tmp_path / "package"
    cache = nested / "cache"
    cache.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    (tmp_path / "root.tmp").write_text("ignored", encoding="utf-8")
    (nested / ".gitignore").write_text(
        "ignored.py\ncache/\n!kept.tmp\n", encoding="utf-8"
    )
    (nested / "ignored.py").write_text("ignored = True\n", encoding="utf-8")
    (nested / "visible.py").write_text("visible = True\n", encoding="utf-8")
    (nested / "kept.tmp").write_text("kept", encoding="utf-8")
    (cache / "generated.py").write_text("generated = True\n", encoding="utf-8")

    paths = {item.path for item in walk_repository(tmp_path)}

    assert "root.tmp" not in paths
    assert "package/ignored.py" not in paths
    assert "package/cache/generated.py" not in paths
    assert "package/visible.py" in paths
    assert "package/kept.tmp" in paths


def test_nested_negation_cannot_reopen_hard_cache_exclusions(tmp_path: Path) -> None:
    """Repository text cannot opt cache directories back into the index."""
    cache = tmp_path / "package" / "__pycache__"
    cache.mkdir(parents=True)
    (tmp_path / "package" / ".gitignore").write_text(
        "!__pycache__/\n!__pycache__/module.py\n", encoding="utf-8"
    )
    (cache / "module.py").write_text("cached = True\n", encoding="utf-8")

    paths = {item.path for item in walk_repository(tmp_path)}

    assert "package/__pycache__/module.py" not in paths

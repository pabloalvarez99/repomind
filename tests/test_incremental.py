"""Content-addressed ingest and incremental-reuse contract tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from repomind.answer import CodeAskService
from repomind.catalog import MalformedRepositoryId, UnknownRepository, catalog_roots
from repomind.ingest import (
    INDEXER_VERSION,
    FileDigest,
    IncrementalIngestor,
    content_hash,
    tree_hash,
)

MINI_FIXTURE = Path(__file__).parents[1] / "fixtures" / "mini_repo"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Return a writable copy of the mini fixture."""
    root = tmp_path / "repo"
    shutil.copytree(MINI_FIXTURE, root)
    return root


def test_every_chunk_carries_a_content_hash(repository: Path) -> None:
    """A definition is addressable by what it is, not only by where it sits."""
    snapshot = IncrementalIngestor(repository).ingest().snapshot

    assert snapshot.chunks
    for chunk in snapshot.chunks:
        assert len(chunk.content_hash) == 64
        assert chunk.content_hash == content_hash(
            kind=chunk.kind, qualname=chunk.qualname, text=chunk.text
        )


def test_the_content_hash_ignores_position_but_not_body(repository: Path) -> None:
    """Moving a definition preserves its address; editing its body does not."""
    same_body_moved = content_hash(kind="function", qualname="f", text="def f():\n    return 1\n")
    edited = content_hash(kind="function", qualname="f", text="def f():\n    return 2\n")
    renamed = content_hash(kind="function", qualname="g", text="def f():\n    return 1\n")

    assert same_body_moved != edited
    assert same_body_moved != renamed


def test_reingesting_an_unchanged_repository_parses_nothing(repository: Path) -> None:
    """The whole point: an unchanged fixture costs no parsing on the second pass."""
    ingestor = IncrementalIngestor(repository)

    first = ingestor.ingest()
    second = ingestor.ingest()

    assert first.stats.parsed_files > 0
    assert second.stats.parsed_files == 0
    assert second.stats.reused_files == first.stats.parsed_files
    assert second.stats.dropped_files == 0
    assert second.stats.is_noop


def test_an_unchanged_reingest_produces_an_identical_snapshot(repository: Path) -> None:
    """A no-op ingest must also be a no-op in what it returns."""
    ingestor = IncrementalIngestor(repository)

    first = ingestor.ingest().snapshot
    second = ingestor.ingest().snapshot

    assert first.tree_hash == second.tree_hash
    assert first.files == second.files
    assert first.chunks == second.chunks


def test_rewriting_a_file_with_identical_bytes_is_still_a_no_op(repository: Path) -> None:
    """Reuse is decided by content, not by a modification timestamp."""
    ingestor = IncrementalIngestor(repository)
    ingestor.ingest()
    target = repository / "app" / "main.py"
    target.write_bytes(target.read_bytes())

    second = ingestor.ingest()

    assert second.stats.parsed_files == 0


def test_only_the_edited_file_is_reparsed(repository: Path) -> None:
    """Incremental means proportional to the change, not to the repository."""
    ingestor = IncrementalIngestor(repository)
    first = ingestor.ingest()
    target = repository / "app" / "service.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n\ndef added() -> int:\n    return 1\n",
        encoding="utf-8",
    )

    second = ingestor.ingest()

    assert second.stats.parsed_files == 1
    assert second.stats.reused_files == first.stats.parsed_files - 1
    assert second.snapshot.tree_hash != first.snapshot.tree_hash
    assert any(chunk.qualname == "added" for chunk in second.snapshot.chunks)


def test_a_deleted_file_drops_out_of_the_index(repository: Path) -> None:
    """A stale cache entry cannot outlive the file that produced it."""
    ingestor = IncrementalIngestor(repository)
    ingestor.ingest()
    (repository / "app" / "service.py").unlink()

    second = ingestor.ingest()

    assert second.stats.dropped_files == 1
    assert not second.stats.is_noop
    assert all(chunk.path != "app/service.py" for chunk in second.snapshot.chunks)


def test_line_endings_do_not_change_the_address(tmp_path: Path) -> None:
    """The same commit checked out CRLF and LF must hash to the same tree."""
    body = "def f():\n    return 1\n"
    unix_root = tmp_path / "unix"
    windows_root = tmp_path / "windows"
    for root, text in ((unix_root, body), (windows_root, body.replace("\n", "\r\n"))):
        root.mkdir()
        (root / "m.py").write_bytes(text.encode("utf-8"))

    unix = IncrementalIngestor(unix_root).ingest().snapshot
    windows = IncrementalIngestor(windows_root).ingest().snapshot

    assert unix.tree_hash == windows.tree_hash
    assert unix.chunks[0].content_hash == windows.chunks[0].content_hash


def test_the_tree_hash_covers_paths_not_only_contents() -> None:
    """Moving a file changes the tree even when no byte of content does."""
    here = (FileDigest(path="a.py", blob_hash="00"), FileDigest(path="b.py", blob_hash="11"))
    moved = (FileDigest(path="a.py", blob_hash="00"), FileDigest(path="c.py", blob_hash="11"))

    assert tree_hash(here) != tree_hash(moved)


def test_the_tree_hash_is_order_independent() -> None:
    """Walk order is an implementation detail; the address must not depend on it."""
    files = (FileDigest(path="a.py", blob_hash="00"), FileDigest(path="b.py", blob_hash="11"))

    assert tree_hash(files) == tree_hash(tuple(reversed(files)))


def test_the_indexer_version_is_part_of_the_address() -> None:
    """The same bytes read by different chunking rules are not the same index."""
    files = (FileDigest(path="a.py", blob_hash="00"),)

    assert tree_hash(files, indexer_version="1") != tree_hash(files, indexer_version="2")


def test_a_new_indexer_version_never_reuses_old_chunks(repository: Path) -> None:
    """Reuse across a rules change would hand back chunks the rules forbid."""
    first = IncrementalIngestor(repository, indexer_version=INDEXER_VERSION).ingest().snapshot
    upgraded = IncrementalIngestor(repository, indexer_version="99").ingest().snapshot

    assert first.tree_hash != upgraded.tree_hash
    assert upgraded.indexer_version == "99"


def test_ingest_counts_all_visible_files_but_indexes_only_python(repository: Path) -> None:
    """The reported counts distinguish what was seen from what was parsed."""
    snapshot = IncrementalIngestor(repository).ingest().snapshot

    paths = {digest.path for digest in snapshot.files}
    assert "README.md" in paths
    assert snapshot.file_count > snapshot.indexed_file_count
    assert snapshot.indexed_file_count == sum(1 for path in paths if path.endswith(".py"))


def test_the_service_reindexes_a_committed_fixture_as_a_no_op() -> None:
    """Restating the guarantee at the level a caller actually uses."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))
    before = service.catalog()

    stats = service.reindex(repo_id="production_rag")

    assert stats.is_noop
    assert stats.parsed_files == 0
    assert stats.reused_files > 0
    assert service.catalog() == before


def test_the_service_reindex_obeys_the_one_validity_function() -> None:
    """Reindex is a catalog operation, so it rejects ids like every other surface."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))

    with pytest.raises(UnknownRepository):
        service.reindex(repo_id="unknown")
    with pytest.raises(MalformedRepositoryId):
        service.reindex(repo_id="../../etc")


def test_the_service_catalog_reports_both_committed_fixtures() -> None:
    """Catalog metadata comes from the snapshot the service actually answers from."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))

    entries = {entry.repo_id: entry for entry in service.catalog()}

    assert set(entries) == {"mini", "production_rag"}
    assert entries["mini"].tree_hash != entries["production_rag"].tree_hash
    assert all(entry.indexer_version == INDEXER_VERSION for entry in entries.values())


def test_ingest_obeys_the_same_gitignore_boundary_as_the_walker(repository: Path) -> None:
    """Content addressing does not become a way around the visibility rules."""
    snapshot = IncrementalIngestor(repository).ingest().snapshot

    paths = {digest.path for digest in snapshot.files}
    assert "ignored.py" not in paths
    assert all("must_not_be_indexed" not in chunk.qualname for chunk in snapshot.chunks)

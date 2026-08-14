"""Content-addressed repository ingest that reuses unchanged work.

Re-reading a fixture is cheap; re-parsing every definition in it is not, and it
also makes "did anything change?" unanswerable. This module gives every file a
blob hash and every repository a tree hash derived from those, so an unchanged
snapshot is provably unchanged and costs no parsing at all.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from repomind.ingest.chunk_javascript import JS_SUFFIXES, chunk_javascript_source
from repomind.ingest.chunk_python import CodeChunk, chunk_python_source, normalize_source
from repomind.ingest.walk import walk_repository

INDEXER_VERSION: Final = "2"
"""Identity of the chunking rules.

Bump this whenever chunk boundaries, ids, or content addresses change meaning. It
is part of every cache key, so an ingestor built by an older indexer can never
hand back chunks an upgraded one would not produce. Version 2 adds free-path
JavaScript/TypeScript top-level definition chunks alongside Python AST chunks.
"""

PYTHON_SUFFIX: Final = ".py"
INDEXED_SUFFIXES: Final = frozenset({PYTHON_SUFFIX, *JS_SUFFIXES})


def _blob_hash(data: bytes) -> str:
    """Return the content address of one file's normalized bytes."""
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class FileDigest:
    """One visible file and the content address of its normalized bytes."""

    path: str
    blob_hash: str


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """An immutable, addressable view of one repository root."""

    indexer_version: str
    tree_hash: str
    files: tuple[FileDigest, ...]
    chunks: tuple[CodeChunk, ...]

    @property
    def file_count(self) -> int:
        """Return how many files the walker considered visible."""
        return len(self.files)

    @property
    def indexed_file_count(self) -> int:
        """Return how many of those files were parsed into definitions."""
        return sum(
            1
            for digest in self.files
            if Path(digest.path).suffix.lower() in INDEXED_SUFFIXES
        )

    @property
    def chunk_count(self) -> int:
        """Return how many definitions the snapshot addresses."""
        return len(self.chunks)


@dataclass(frozen=True, slots=True)
class IngestStats:
    """What one ingest actually did, as opposed to what it produced."""

    parsed_files: int
    reused_files: int
    dropped_files: int

    @property
    def is_noop(self) -> bool:
        """Return whether the ingest parsed nothing and discarded nothing."""
        return self.parsed_files == 0 and self.dropped_files == 0


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    """A snapshot plus the work that produced it."""

    snapshot: RepositorySnapshot
    stats: IngestStats


def tree_hash(files: tuple[FileDigest, ...], *, indexer_version: str = INDEXER_VERSION) -> str:
    """Return one address for a whole file set.

    Path and blob hash are both folded in, so moving a file changes the tree even
    when no byte of content does. The indexer version is folded in too: the same
    bytes read by different chunking rules are not the same index.
    """
    digest = hashlib.sha256()
    digest.update(f"repomind-tree-v{indexer_version}\x00".encode())
    for entry in sorted(files, key=lambda item: item.path):
        digest.update(f"{entry.path}\x00{entry.blob_hash}\x00".encode())
    return digest.hexdigest()


class IncrementalIngestor:
    """Ingest one repository root, reusing chunks whose bytes did not change.

    The cache is keyed by repository-relative path and validated by blob hash, so
    a stale entry cannot survive an edit and a moved file cannot inherit another
    file's chunks. The ingestor holds no filesystem path from any caller: it is
    constructed with a root the catalog resolved.
    """

    def __init__(self, root: Path, *, indexer_version: str = INDEXER_VERSION) -> None:
        """Bind an ingestor to one already-resolved repository root."""
        self._root = root
        self._indexer_version = indexer_version
        self._cache: dict[str, tuple[str, tuple[CodeChunk, ...]]] = {}

    @property
    def indexer_version(self) -> str:
        """Return the chunking-rule identity this ingestor produces."""
        return self._indexer_version

    def ingest(self) -> IngestOutcome:
        """Walk the root and return an addressable snapshot.

        Files whose blob hash matches the cache are not re-read past their bytes
        and not re-parsed. A second ingest of an unchanged tree parses nothing.

        Raises:
            ValueError: The bound root is not a directory.
            SyntaxError: A visible Python file is not valid Python.
        """
        digests: list[FileDigest] = []
        chunks: list[CodeChunk] = []
        fresh: dict[str, tuple[str, tuple[CodeChunk, ...]]] = {}
        parsed = 0
        reused = 0

        for repository_file in walk_repository(self._root):
            data = repository_file.absolute_path.read_bytes()
            suffix = repository_file.absolute_path.suffix.lower()
            if suffix not in INDEXED_SUFFIXES:
                # Addressed by the bytes on disk, which is all the walker promises.
                digests.append(
                    FileDigest(path=repository_file.path, blob_hash=_blob_hash(data))
                )
                continue

            # Source files are addressed by their normalized text instead, so a
            # CRLF checkout and an LF checkout of one commit agree on the tree.
            source = normalize_source(data)
            blob = _blob_hash(source.encode("utf-8"))
            digests.append(FileDigest(path=repository_file.path, blob_hash=blob))

            cached = self._cache.get(repository_file.path)
            if cached is not None and cached[0] == blob:
                file_chunks = cached[1]
                reused += 1
            else:
                if suffix == PYTHON_SUFFIX:
                    file_chunks = chunk_python_source(source, path=repository_file.path)
                else:
                    file_chunks = chunk_javascript_source(
                        source, path=repository_file.path
                    )
                parsed += 1
            fresh[repository_file.path] = (blob, file_chunks)
            chunks.extend(file_chunks)

        dropped = len(set(self._cache) - set(fresh))
        self._cache = fresh
        files = tuple(digests)
        snapshot = RepositorySnapshot(
            indexer_version=self._indexer_version,
            tree_hash=tree_hash(files, indexer_version=self._indexer_version),
            files=files,
            chunks=tuple(chunks),
        )
        return IngestOutcome(
            snapshot=snapshot,
            stats=IngestStats(parsed_files=parsed, reused_files=reused, dropped_files=dropped),
        )

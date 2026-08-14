"""Repository discovery and content-addressed, source-aware chunking."""

from repomind.ingest.chunk_python import (
    CodeChunk,
    chunk_python_file,
    chunk_python_source,
    chunk_repository,
    content_hash,
    normalize_source,
)
from repomind.ingest.incremental import (
    INDEXER_VERSION,
    FileDigest,
    IncrementalIngestor,
    IngestOutcome,
    IngestStats,
    RepositorySnapshot,
    tree_hash,
)
from repomind.ingest.walk import RepositoryFile, walk_repository

__all__ = [
    "INDEXER_VERSION",
    "CodeChunk",
    "FileDigest",
    "IncrementalIngestor",
    "IngestOutcome",
    "IngestStats",
    "RepositoryFile",
    "RepositorySnapshot",
    "chunk_python_file",
    "chunk_python_source",
    "chunk_repository",
    "content_hash",
    "normalize_source",
    "tree_hash",
    "walk_repository",
]

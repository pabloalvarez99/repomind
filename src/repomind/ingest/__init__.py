"""Repository discovery and content-addressed, source-aware chunking."""

from repomind.ingest.chunk_javascript import (
    JS_SUFFIXES,
    chunk_javascript_file,
    chunk_javascript_repository,
    chunk_javascript_source,
    try_chunk_with_treesitter,
)
from repomind.ingest.chunk_python import (
    CodeChunk,
    chunk_python_file,
    chunk_python_source,
    chunk_repository,
    content_hash,
    normalize_source,
)
from repomind.ingest.incremental import (
    INDEXED_SUFFIXES,
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
    "INDEXED_SUFFIXES",
    "INDEXER_VERSION",
    "JS_SUFFIXES",
    "CodeChunk",
    "FileDigest",
    "IncrementalIngestor",
    "IngestOutcome",
    "IngestStats",
    "RepositoryFile",
    "RepositorySnapshot",
    "chunk_javascript_file",
    "chunk_javascript_repository",
    "chunk_javascript_source",
    "chunk_python_file",
    "chunk_python_source",
    "chunk_repository",
    "content_hash",
    "normalize_source",
    "tree_hash",
    "try_chunk_with_treesitter",
    "walk_repository",
]

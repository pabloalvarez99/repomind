"""Structural JSON chunks via the stdlib ``json`` module (no network).

Each top-level object key becomes one ``field`` chunk with a best-effort line
range. Nested objects are not exploded in v1 — honesty label is structural
navigation, not a schema language.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from repomind.ingest.chunk_python import (
    ChunkKind,
    CodeChunk,
    content_hash,
    normalize_source,
)

JSON_SUFFIXES: frozenset[str] = frozenset({".json"})

__all__ = [
    "JSON_SUFFIXES",
    "chunk_json_file",
    "chunk_json_source",
]


def _line_of_key(source: str, key: str) -> int | None:
    """Return the 1-based line of the first JSON object key occurrence."""
    pattern = re.compile(rf'"{re.escape(key)}"\s*:')
    for index, line in enumerate(source.splitlines(), start=1):
        if pattern.search(line):
            return index
    return None


def chunk_json_source(source: str, *, path: str) -> tuple[CodeChunk, ...]:
    """Chunk top-level object keys from a JSON document.

    Arrays and non-object roots yield no chunks (not an error): there is no
    named definition to cite.
    """
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, dict):
        return ()

    chunks: list[CodeChunk] = []
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            continue
        start = _line_of_key(text, key) or 1
        snippet = json.dumps({key: value}, ensure_ascii=True, indent=2)
        if not snippet.endswith("\n"):
            snippet = snippet + "\n"
        end = start + max(snippet.count("\n") - 1, 0)
        kind: ChunkKind = "field"
        qualname = key
        chunk_id = f"{path}::{qualname}"
        chunks.append(
            CodeChunk(
                chunk_id=chunk_id,
                path=path,
                qualname=qualname,
                kind=kind,
                start_line=start,
                end_line=max(end, start),
                text=snippet,
                content_hash=content_hash(kind=kind, qualname=qualname, text=snippet),
            )
        )
    return tuple(chunks)


def chunk_json_file(path: Path, *, relative_path: str | None = None) -> tuple[CodeChunk, ...]:
    """Read one JSON file and return structural field chunks."""
    rel = relative_path if relative_path is not None else path.name
    data = path.read_bytes()
    return chunk_json_source(normalize_source(data), path=rel)

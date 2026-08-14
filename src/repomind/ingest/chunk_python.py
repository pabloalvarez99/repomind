"""AST-aware Python chunks with exact source boundaries."""

from __future__ import annotations

import ast
import hashlib
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from repomind.ingest.walk import walk_repository

# Shared by Python AST and free-path JS/TS scanners. Keep the set small so the
# answer renderer and index stay language-agnostic.
# ``field`` is used by structural JSON/TOML packs (stdlib parsers, no network).
ChunkKind = Literal["class", "function", "async_function", "field"]

__all__ = [
    "ChunkKind",
    "CodeChunk",
    "chunk_python_file",
    "chunk_python_source",
    "chunk_repository",
    "content_hash",
    "normalize_source",
]


def content_hash(*, kind: str, qualname: str, text: str) -> str:
    """Return the content address of one definition.

    The address covers what the definition *is* -- its kind, its qualified name,
    and its exact source text -- and deliberately not where it sits. A definition
    that moves down its file keeps its hash; a definition whose body or name
    changes gets a new one. Fields are joined with a separator that cannot occur
    inside them, so no pair of different definitions can collide by concatenation.
    """
    payload = "\x00".join((kind, qualname, text)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_source(data: bytes) -> str:
    """Decode Python source and normalize line endings before any hashing.

    Honors a PEP 263 encoding declaration the way :func:`tokenize.open` does, then
    collapses CRLF. Without that, the same commit checked out on Windows and on
    Linux would produce different hashes for byte-identical history.
    """
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """One addressable Python definition and its original source text."""

    chunk_id: str
    path: str
    qualname: str
    kind: ChunkKind
    start_line: int
    end_line: int
    text: str
    content_hash: str


class _DefinitionVisitor(ast.NodeVisitor):
    """Collect definitions while tracking their lexical qualified names."""

    def __init__(self, *, path: str, lines: list[str]) -> None:
        self._path = path
        self._lines = lines
        self._parents: list[str] = []
        self.chunks: list[CodeChunk] = []

    def _record(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_line = node.end_lineno
        if end_line is None:  # pragma: no cover - guaranteed by Python 3.12's parser
            raise ValueError(f"definition has no end line: {self._path}:{node.lineno}")
        qualname = ".".join((*self._parents, node.name))
        kind: ChunkKind
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        else:
            kind = "function"
        text = "".join(self._lines[node.lineno - 1 : end_line])
        self.chunks.append(
            CodeChunk(
                chunk_id=f"{self._path}::{qualname}",
                path=self._path,
                qualname=qualname,
                kind=kind,
                start_line=node.lineno,
                end_line=end_line,
                text=text,
                content_hash=content_hash(kind=kind, qualname=qualname, text=text),
            )
        )
        self._parents.append(node.name)
        self.generic_visit(node)
        self._parents.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802 - ast visitor API
        """Record a class and visit definitions nested inside it."""
        self._record(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802 - ast visitor API
        """Record a function or method and visit nested definitions."""
        self._record(node)

    def visit_AsyncFunctionDef(  # noqa: N802 - ast visitor API
        self, node: ast.AsyncFunctionDef
    ) -> None:
        """Record an async function or method and visit nested definitions."""
        self._record(node)


def chunk_python_source(source: str, *, path: str) -> tuple[CodeChunk, ...]:
    """Parse already-decoded Python source into definition chunks.

    Taking text rather than a path lets a caller that has already read and hashed
    the bytes chunk them without a second read.

    Args:
        source: Decoded Python source, line endings normalized.
        path: Stable POSIX path relative to the repository root.

    Returns:
        Chunks in source order.

    Raises:
        SyntaxError: The source is not valid Python.
    """
    tree = ast.parse(source, filename=path)
    visitor = _DefinitionVisitor(path=path, lines=source.splitlines(keepends=True))
    visitor.visit(tree)
    return tuple(visitor.chunks)


def chunk_python_file(file: Path, *, path: str) -> tuple[CodeChunk, ...]:
    """Parse one Python file into definition chunks.

    Args:
        file: Absolute or caller-resolved Python source path.
        path: Stable POSIX path relative to the repository root.

    Returns:
        Chunks in source order.

    Raises:
        SyntaxError: The source is not valid Python.
    """
    return chunk_python_source(normalize_source(file.read_bytes()), path=path)


def chunk_repository(root: Path) -> tuple[CodeChunk, ...]:
    """Walk ``root`` and chunk every visible Python file deterministically."""
    chunks: list[CodeChunk] = []
    for file in walk_repository(root):
        if file.absolute_path.suffix == ".py":
            chunks.extend(chunk_python_file(file.absolute_path, path=file.path))
    return tuple(chunks)

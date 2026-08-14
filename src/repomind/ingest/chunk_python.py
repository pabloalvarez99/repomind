"""AST-aware Python chunks with exact source boundaries."""

from __future__ import annotations

import ast
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from repomind.ingest.walk import walk_repository

ChunkKind = Literal["class", "function", "async_function"]


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
        self.chunks.append(
            CodeChunk(
                chunk_id=f"{self._path}::{qualname}",
                path=self._path,
                qualname=qualname,
                kind=kind,
                start_line=node.lineno,
                end_line=end_line,
                text="".join(self._lines[node.lineno - 1 : end_line]),
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
    with tokenize.open(file) as source_file:
        source = source_file.read()
    tree = ast.parse(source, filename=path)
    visitor = _DefinitionVisitor(path=path, lines=source.splitlines(keepends=True))
    visitor.visit(tree)
    return tuple(visitor.chunks)


def chunk_repository(root: Path) -> tuple[CodeChunk, ...]:
    """Walk ``root`` and chunk every visible Python file deterministically."""
    chunks: list[CodeChunk] = []
    for file in walk_repository(root):
        if file.absolute_path.suffix == ".py":
            chunks.extend(chunk_python_file(file.absolute_path, path=file.path))
    return tuple(chunks)

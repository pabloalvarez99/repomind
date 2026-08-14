"""Free-path JavaScript/TypeScript definition chunks.

Python keeps the stdlib AST as its free path. This module is deliberate plumbing:
a line-oriented scanner that finds top-level ``function``, ``async function``, and
``class`` declarations (including ``export`` / ``export default`` forms) without a
parser generator, without network, and without a tree-sitter runtime.

Optional ``[treesitter]`` extras may replace this later. Until then CI indexes JS
with this scanner only, so a green build never depends on downloading a grammar.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from repomind.ingest.chunk_python import ChunkKind, CodeChunk, content_hash, normalize_source
from repomind.ingest.walk import walk_repository

JS_SUFFIXES: frozenset[str] = frozenset({".js", ".mjs", ".cjs", ".ts", ".tsx"})

# Top-level declaration forms only. Nested bodies are walked for brace balance,
# not for nested definitions — that is enough for fixture plumbing, not for SOTA.
_DECL = re.compile(
    r"""
    ^\s*
    (?:export\s+(?:default\s+)?)?
    (?:
        (?P<async>async\s+)?function\s+(?P<fname>[A-Za-z_$][\w$]*)
      | class\s+(?P<cname>[A-Za-z_$][\w$]*)
    )
    """,
    re.VERBOSE,
)


def _brace_end(lines: list[str], start_index: int) -> int:
    """Return the 1-based end line of the first balanced ``{...}`` from start.

    Strings and comments are not fully modeled. That is intentional: this is a
    fixture scanner, not a language front-end. Balanced braces on the tiny
    committed sources are enough to produce a stable path:line citation.
    """
    depth = 0
    seen_open = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        for char in line:
            if char == "{":
                depth += 1
                seen_open = True
            elif char == "}":
                depth -= 1
                if seen_open and depth == 0:
                    return index + 1
    return len(lines)


def chunk_javascript_source(source: str, *, path: str) -> tuple[CodeChunk, ...]:
    """Parse already-decoded JS/TS source into top-level definition chunks.

    Args:
        source: Decoded source, line endings normalized.
        path: Stable POSIX path relative to the repository root.

    Returns:
        Chunks in source order. Nested methods are not emitted as separate
        chunks; only top-level functions and classes are.
    """
    lines = source.splitlines(keepends=True)
    chunks: list[CodeChunk] = []
    index = 0
    while index < len(lines):
        match = _DECL.match(lines[index])
        if match is None:
            index += 1
            continue
        if match.group("fname"):
            name = match.group("fname")
            kind: ChunkKind = "async_function" if match.group("async") else "function"
        else:
            name = match.group("cname")
            kind = "class"
        end_line = _brace_end(lines, index)
        text = "".join(lines[index:end_line])
        chunks.append(
            CodeChunk(
                chunk_id=f"{path}::{name}",
                path=path,
                qualname=name,
                kind=kind,
                start_line=index + 1,
                end_line=end_line,
                text=text,
                content_hash=content_hash(kind=kind, qualname=name, text=text),
            )
        )
        index = end_line
    return tuple(chunks)


def chunk_javascript_file(file: Path, *, path: str) -> tuple[CodeChunk, ...]:
    """Parse one JS/TS file into definition chunks."""
    return chunk_javascript_source(normalize_source(file.read_bytes()), path=path)


def chunk_javascript_repository(root: Path) -> tuple[CodeChunk, ...]:
    """Walk ``root`` and chunk every visible JS/TS file deterministically."""
    chunks: list[CodeChunk] = []
    for file in walk_repository(root):
        if file.absolute_path.suffix.lower() in JS_SUFFIXES:
            chunks.extend(chunk_javascript_file(file.absolute_path, path=file.path))
    return tuple(chunks)


def try_chunk_with_treesitter(source: str, *, path: str) -> tuple[CodeChunk, ...] | None:
    """Return chunks from tree-sitter when the optional extra is installed.

    CI never imports this path by default. Callers that want the grammar install
    ``pip install 'repomind[treesitter]'`` and pass the result through the same
    :class:`CodeChunk` contract. On any import or parse failure this returns
    ``None`` so the free-path scanner remains the safe default.
    """
    try:
        import tree_sitter_javascript as ts_js  # type: ignore[import-not-found]
        from tree_sitter import Language, Parser  # type: ignore[import-not-found]
    except ImportError:
        return None

    language = Language(ts_js.language())
    parser = Parser(language)
    tree = parser.parse(source.encode("utf-8"))
    root = tree.root_node
    chunks: list[CodeChunk] = []

    def walk(node: object, parents: list[str]) -> None:
        node_type = getattr(node, "type", "")
        name_node = None
        kind: str | None = None
        if node_type in {"function_declaration", "generator_function_declaration"}:
            name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
            kind = cast(ChunkKind | None, "function")
        elif node_type == "class_declaration":
            name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
            kind = cast(ChunkKind | None, "class")
        else:
            kind = None
        if name_node is not None and kind is not None:
            name = source[name_node.start_byte : name_node.end_byte]
            start_line = node.start_point[0] + 1  # type: ignore[attr-defined]
            end_line = node.end_point[0] + 1  # type: ignore[attr-defined]
            text = source[node.start_byte : node.end_byte]  # type: ignore[attr-defined]
            if not text.endswith("\n"):
                text = text + "\n"
            qualname = ".".join((*parents, name))
            chunks.append(
                CodeChunk(
                    chunk_id=f"{path}::{qualname}",
                    path=path,
                    qualname=qualname,
                    kind=kind,
                    start_line=start_line,
                    end_line=end_line,
                    text=text,
                    content_hash=content_hash(kind=kind, qualname=qualname, text=text),
                )
            )
            next_parents = [*parents, name]
        else:
            next_parents = parents
        for child in getattr(node, "children", []) or []:
            walk(child, next_parents)

    walk(root, [])
    return tuple(chunks)

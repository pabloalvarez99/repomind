"""Language pack registry for free-path indexing.

Default CI never downloads grammars. Packs that need optional native deps
(tree-sitter) stay behind extras and are not required to answer goldens.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from repomind.ingest.chunk_javascript import JS_SUFFIXES, chunk_javascript_source
from repomind.ingest.chunk_json import JSON_SUFFIXES, chunk_json_source
from repomind.ingest.chunk_python import CodeChunk, chunk_python_source

PYTHON_SUFFIX: Final = ".py"


@dataclass(frozen=True, slots=True)
class LanguagePack:
    """One offline language surface the indexer can call.

    Attributes:
        pack_id: Stable id shown in docs and honesty labels.
        suffixes: File suffixes this pack claims (lowercase, with dot).
        honesty_label: What the pack is allowed to claim in UI/docs.
        chunk: Pure function source → chunks for a repository-relative path.
        default: Whether the pack is on the free path without extras.
    """

    pack_id: str
    suffixes: frozenset[str]
    honesty_label: str
    chunk: Callable[[str, str], tuple[CodeChunk, ...]]
    default: bool = True


def _chunk_python(source: str, path: str) -> tuple[CodeChunk, ...]:
    return chunk_python_source(source, path=path)


def _chunk_js(source: str, path: str) -> tuple[CodeChunk, ...]:
    return chunk_javascript_source(source, path=path)


def _chunk_json(source: str, path: str) -> tuple[CodeChunk, ...]:
    return chunk_json_source(source, path=path)


PYTHON_AST_PACK: Final = LanguagePack(
    pack_id="python-ast",
    suffixes=frozenset({PYTHON_SUFFIX}),
    honesty_label="stdlib ast definitions; lexical navigation, not semantic search",
    chunk=_chunk_python,
    default=True,
)

JS_PACK: Final = LanguagePack(
    pack_id="js",
    suffixes=JS_SUFFIXES,
    honesty_label="pure free-path scanner; optional tree-sitter extra never required in CI",
    chunk=_chunk_js,
    default=True,
)

JSON_PACK: Final = LanguagePack(
    pack_id="json",
    suffixes=JSON_SUFFIXES,
    honesty_label="stdlib json top-level keys only; vendored/no network",
    chunk=_chunk_json,
    default=True,
)

PACKS: Final = (PYTHON_AST_PACK, JS_PACK, JSON_PACK)


def pack_for_suffix(suffix: str) -> LanguagePack | None:
    """Return the pack that owns ``suffix``, or None when the file is not indexed."""
    lowered = suffix.lower()
    for pack in PACKS:
        if lowered in pack.suffixes:
            return pack
    return None


def indexed_suffixes() -> frozenset[str]:
    """Return the union of all free-path pack suffixes."""
    owned: set[str] = set()
    for pack in PACKS:
        owned.update(pack.suffixes)
    return frozenset(owned)


def chunk_source_for_path(source: str, *, path: str, suffix: str) -> tuple[CodeChunk, ...]:
    """Dispatch source text to the pack that owns the suffix."""
    pack = pack_for_suffix(suffix)
    if pack is None:
        return ()
    return pack.chunk(source, path)

"""A small deterministic index for symbols and source terms."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from repomind.ingest.chunk_python import CodeChunk

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_STOPWORD_TEXT: Final = (
    "a an and are by code defined definition does for from how in is it of on the to what "
    "where which with"
)
_STOPWORDS: Final = frozenset(_STOPWORD_TEXT.split())


def terms(text: str) -> frozenset[str]:
    """Return normalized identifier-aware terms from prose or source code."""
    found: set[str] = set()
    for token in _WORD.findall(text):
        folded = token.casefold()
        if folded not in _STOPWORDS:
            found.add(folded)
        expanded = _CAMEL_BOUNDARY.sub("_", token).split("_")
        found.update(
            part.casefold()
            for part in expanded
            if part and part.casefold() not in _STOPWORDS
        )
    return frozenset(found)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A chunk plus transparent lexical relevance evidence."""

    chunk: CodeChunk
    score: int
    matched_terms: tuple[str, ...]


class InMemoryCodeIndex:
    """Immutable lexical index over AST chunks."""

    def __init__(self, chunks: tuple[CodeChunk, ...]) -> None:
        """Index chunks without reading files or contacting a service."""
        self._chunks = tuple(chunks)

    @property
    def size(self) -> int:
        """Return the number of indexed definitions."""
        return len(self._chunks)

    def locate_symbol(self, symbol: str) -> tuple[CodeChunk, ...]:
        """Return exact qualified-name or leaf-name matches."""
        wanted = symbol.casefold().strip()
        matches = [
            chunk
            for chunk in self._chunks
            if chunk.qualname.casefold() == wanted
            or chunk.qualname.rsplit(".", maxsplit=1)[-1].casefold() == wanted
        ]
        return tuple(sorted(matches, key=lambda chunk: chunk.chunk_id))

    def search(self, question: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        """Rank chunks by exact symbol match and lexical overlap.

        Args:
            question: Natural-language or identifier query.
            limit: Maximum results. Must be positive.

        Returns:
            Positive-scoring results in deterministic order.

        Raises:
            ValueError: ``limit`` is not positive.
        """
        if limit < 1:
            raise ValueError("search limit must be positive")
        query_terms = terms(question)
        if not query_terms:
            return ()

        ranked: list[SearchResult] = []
        for chunk in self._chunks:
            leaf = chunk.qualname.rsplit(".", maxsplit=1)[-1].casefold()
            symbol_terms = terms(chunk.qualname)
            path_terms = terms(chunk.path)
            text_terms = terms(chunk.text)
            symbol_overlap = query_terms & symbol_terms
            path_overlap = query_terms & path_terms
            text_overlap = query_terms & text_terms
            exact = leaf in query_terms or chunk.qualname.casefold() in query_terms
            score = (
                (100 if exact else 0)
                + 10 * len(symbol_overlap)
                + 3 * len(path_overlap)
                + len(text_overlap)
            )
            if score:
                matched = tuple(sorted(symbol_overlap | path_overlap | text_overlap))
                ranked.append(SearchResult(chunk=chunk, score=score, matched_terms=matched))

        ranked.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
        return tuple(ranked[:limit])

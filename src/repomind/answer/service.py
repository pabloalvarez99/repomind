"""Deterministic code-question service over named repository indexes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from repomind.answer.models import CodeAnswer, CodeCitation, CodeSymbol
from repomind.catalog import MINI_REPO_ID, UnknownRepository, validate_repo_id
from repomind.index import InMemoryCodeIndex, SearchResult
from repomind.ingest import chunk_repository

REFUSAL: Final = "I could not find code evidence that answers this question."
MAX_CITATIONS: Final = 3

__all__ = ["MAX_CITATIONS", "REFUSAL", "CodeAskService", "UnknownRepository"]


def _snippet(result: SearchResult) -> str:
    """Return a compact single-line source preview."""
    compact = " ".join(result.chunk.text.split())
    return compact if len(compact) <= 240 else compact[:237] + "..."


def _render_result(result: SearchResult, marker: int) -> str:
    """Render one retrieved definition without inferring its behavior."""
    chunk = result.chunk
    kind = chunk.kind.replace("_", " ")
    article = "an" if kind.startswith("a") else "a"
    return (
        f"[{marker}] `{chunk.qualname}` is {article} {kind} in "
        f"`{chunk.path}` at lines {chunk.start_line}-{chunk.end_line}."
    )


class CodeAskService:
    """Answer from one of a fixed set of in-memory repository indexes."""

    def __init__(self, indexes: Mapping[str, InMemoryCodeIndex]) -> None:
        """Store an immutable copy of the allowed repository catalog."""
        self._indexes = dict(indexes)

    @classmethod
    def from_roots(cls, roots: Mapping[str, Path]) -> CodeAskService:
        """Build one AST index per configured repository id."""
        return cls(
            {
                repo_id: InMemoryCodeIndex(chunk_repository(root))
                for repo_id, root in roots.items()
            }
        )

    def _index_for(self, repo_id: str) -> InMemoryCodeIndex:
        """Resolve a caller-supplied id through the one validity function.

        Raises:
            BlankRepositoryId: ``repo_id`` is empty or only whitespace.
            MalformedRepositoryId: ``repo_id`` is not a catalog identifier.
            UnknownRepository: ``repo_id`` is not in this service's catalog.
        """
        return self._indexes[validate_repo_id(repo_id, known=self._indexes)]

    def ask(self, question: str, *, repo_id: str = MINI_REPO_ID) -> CodeAnswer:
        """Answer ``question`` from retrieved definitions or refuse.

        Raises:
            BlankRepositoryId: ``repo_id`` is empty or only whitespace.
            MalformedRepositoryId: ``repo_id`` is not a catalog identifier.
            UnknownRepository: ``repo_id`` is not in the configured catalog.
        """
        index = self._index_for(repo_id)

        results = index.search(question, limit=MAX_CITATIONS)
        if not results:
            return CodeAnswer(answer=REFUSAL, citations=[])

        answer = "\n".join(
            _render_result(result, marker) for marker, result in enumerate(results, 1)
        )
        citations = [
            CodeCitation(
                path=result.chunk.path,
                start_line=result.chunk.start_line,
                end_line=result.chunk.end_line,
                snippet=_snippet(result),
            )
            for result in results
        ]
        return CodeAnswer(answer=answer, citations=citations)

    def symbols(self, *, repo_id: str = MINI_REPO_ID) -> list[CodeSymbol]:
        """Return a stable source outline for one configured repository.

        Raises:
            BlankRepositoryId: ``repo_id`` is empty or only whitespace.
            MalformedRepositoryId: ``repo_id`` is not a catalog identifier.
            UnknownRepository: ``repo_id`` is not in the configured catalog.
        """
        index = self._index_for(repo_id)

        return [
            CodeSymbol(
                path=chunk.path,
                qualname=chunk.qualname,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                kind=chunk.kind,
            )
            for chunk in index.chunks
        ]

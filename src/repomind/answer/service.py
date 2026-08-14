"""Deterministic code-question service over named repository indexes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from repomind.answer.models import (
    CallSiteModel,
    CodeAnswer,
    CodeCitation,
    CodeSymbol,
    IncomingRefsResponse,
    RepositoryMetadata,
)
from repomind.catalog import MINI_REPO_ID, UnknownRepository, validate_repo_id
from repomind.index import InMemoryCodeIndex, SearchResult
from repomind.ingest import IncrementalIngestor, IngestStats, RepositorySnapshot
from repomind.ingest.call_graph import CallSite, build_incoming_refs, incoming_for

REFUSAL: Final = "I could not find code evidence that answers this question."
MAX_CITATIONS: Final = 3
_SOURCE_META_REL: Final = Path(".repomind") / "source.json"

__all__ = ["MAX_CITATIONS", "REFUSAL", "CodeAskService", "UnknownRepository"]


def _load_source_meta(root: Path) -> tuple[str | None, str | None]:
    """Return optional (source_sha, source_repo) from a fixture pin file."""
    path = root / _SOURCE_META_REL
    if not path.is_file():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    sha = payload.get("source_sha")
    repo = payload.get("upstream")
    return (
        sha if isinstance(sha, str) and sha.strip() else None,
        repo if isinstance(repo, str) and repo.strip() else None,
    )


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

    def __init__(
        self,
        indexes: Mapping[str, InMemoryCodeIndex],
        *,
        ingestors: Mapping[str, IncrementalIngestor] | None = None,
        snapshots: Mapping[str, RepositorySnapshot] | None = None,
        source_meta: Mapping[str, tuple[str | None, str | None]] | None = None,
        roots: Mapping[str, Path] | None = None,
        refs: Mapping[str, Mapping[str, tuple[CallSite, ...]]] | None = None,
    ) -> None:
        """Store an immutable copy of the allowed repository catalog.

        ``ingestors`` and ``snapshots`` are optional so a test may still inject
        bare indexes. Without them the service answers questions but reports no
        catalog metadata, because it has no addressed tree to report.
        """
        self._indexes = dict(indexes)
        self._ingestors = dict(ingestors or {})
        self._snapshots = dict(snapshots or {})
        self._source_meta = dict(source_meta or {})
        self._roots = dict(roots or {})
        self._refs = {repo_id: dict(table) for repo_id, table in (refs or {}).items()}

    @classmethod
    def from_roots(cls, roots: Mapping[str, Path]) -> CodeAskService:
        """Build one content-addressed index per configured repository id."""
        ingestors = {repo_id: IncrementalIngestor(root) for repo_id, root in roots.items()}
        snapshots = {repo_id: ingestor.ingest().snapshot for repo_id, ingestor in ingestors.items()}
        source_meta = {repo_id: _load_source_meta(root) for repo_id, root in roots.items()}
        refs = {
            repo_id: build_incoming_refs(root, definitions=snapshot.chunks)
            for repo_id, (root, snapshot) in (
                (repo_id, (roots[repo_id], snapshots[repo_id])) for repo_id in roots
            )
        }
        return cls(
            {
                repo_id: InMemoryCodeIndex(snapshot.chunks)
                for repo_id, snapshot in snapshots.items()
            },
            ingestors=ingestors,
            snapshots=snapshots,
            source_meta=source_meta,
            roots=roots,
            refs=refs,
        )

    def catalog(self) -> list[RepositoryMetadata]:
        """Return addressable metadata for every repository this service serves."""
        entries: list[RepositoryMetadata] = []
        for repo_id, snapshot in sorted(self._snapshots.items()):
            sha, upstream = self._source_meta.get(repo_id, (None, None))
            entries.append(
                RepositoryMetadata(
                    repo_id=repo_id,
                    file_count=snapshot.file_count,
                    indexed_file_count=snapshot.indexed_file_count,
                    chunk_count=snapshot.chunk_count,
                    tree_hash=snapshot.tree_hash,
                    indexer_version=snapshot.indexer_version,
                    source_sha=sha,
                    source_repo=upstream,
                )
            )
        return entries

    def reindex(self, *, repo_id: str) -> IngestStats:
        """Re-ingest one repository, reusing every file whose bytes are unchanged.

        Returns:
            What the ingest actually did. An unchanged tree parses nothing.

        Raises:
            BlankRepositoryId: ``repo_id`` is empty or only whitespace.
            MalformedRepositoryId: ``repo_id`` is not a catalog identifier.
            UnknownRepository: ``repo_id`` is not in the configured catalog.
        """
        validated = validate_repo_id(repo_id, known=self._ingestors)
        outcome = self._ingestors[validated].ingest()
        self._snapshots[validated] = outcome.snapshot
        self._indexes[validated] = InMemoryCodeIndex(outcome.snapshot.chunks)
        root = self._roots.get(validated)
        if root is not None:
            self._refs[validated] = build_incoming_refs(
                root, definitions=outcome.snapshot.chunks
            )
        return outcome.stats

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

    def incoming_refs(
        self, *, repo_id: str = MINI_REPO_ID, symbol: str
    ) -> IncomingRefsResponse:
        """Return Python AST call sites that name ``symbol`` in a catalog repo.

        Zero callers is a valid leaf. Unknown short names also return zero
        callers rather than inventing edges. Only fixture/catalog roots are
        accepted — the same validity function as every other surface.

        Raises:
            BlankRepositoryId / MalformedRepositoryId / UnknownRepository: bad id.
            ValueError: ``symbol`` is blank.
        """
        if not symbol or not symbol.strip():
            raise ValueError("symbol must not be blank")
        validated = validate_repo_id(repo_id, known=self._indexes)
        table = self._refs.get(validated, {})
        if not table and validated in self._roots:
            snapshot = self._snapshots.get(validated)
            chunks = snapshot.chunks if snapshot is not None else ()
            table = build_incoming_refs(self._roots[validated], definitions=chunks)
            self._refs[validated] = table
        qualname, sites = incoming_for(table, symbol)
        return IncomingRefsResponse(
            repo_id=validated,
            symbol=symbol.strip(),
            qualname=qualname,
            callers=[
                CallSiteModel(
                    path=site.path,
                    line=site.line,
                    caller_qualname=site.caller_qualname,
                    callee_name=site.callee_name,
                )
                for site in sites
            ],
        )

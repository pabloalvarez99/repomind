# Production RAG source snapshot

Source: https://github.com/pabloalvarez99/production-rag at pinned SHA
`bf6e36d1d4ca353c4f17f649cb721da51d74f6bb` (P1 v0.3.0 main / bf6e36d family).

This is a small, read-only snapshot for RepoMind citation tests. It is not a fork
and is not a live clone of P1. The selected Python files under `src/` cover the
public query entry, graph wiring, reciprocal-rank fusion, a deterministic
embedding provider, citation/refusal guardrails, and the `/v1/query` API route.
RepoMind parses them as untrusted text and never imports or executes them.

Machine-readable pin: `.repomind/source.json` (also exposed on `GET /v1/catalog`
as `source_sha` / `source_repo` for this id).

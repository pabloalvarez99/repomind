# Production RAG source snapshot

Source: https://github.com/pabloalvarez99/production-rag at pinned SHA
`3b54d85a9c0d3ba85bd0760058aafce76849d1f7` (P1 v1.0.0 main / 3b54d85 family).

This is a small, read-only snapshot for RepoMind citation tests. It is not a fork
and is not a live clone of P1. The selected Python files under `src/` cover the
public query entry, graph wiring, reciprocal-rank fusion, a deterministic
embedding provider, citation/refusal guardrails, and the `/v1/query` API route.
RepoMind parses them as untrusted text and never imports or executes them.

Machine-readable pin: `.repomind/source.json` (also exposed on `GET /v1/catalog`
as `source_sha` / `source_repo` for this id).

# Production RAG source snapshot

Source: https://github.com/pabloalvarez99/production-rag at approximately `d882c9a`.

This is a small, read-only snapshot for RepoMind citation tests. It is not a fork and is not
kept in sync automatically. The selected Python files cover the public query entry, graph
wiring, reciprocal-rank fusion, a deterministic embedding provider, citation/refusal
guardrails, and the `/v1/query` API route. RepoMind parses them as untrusted text and never
imports or executes them.

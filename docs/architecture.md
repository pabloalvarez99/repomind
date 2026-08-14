# Architecture

RepoMind is a parse-only code navigation service. It turns definitions into stable,
line-addressable evidence without executing repository code or calling a model.

```text
closed repo_id catalog  (mini | production_rag | mini_js)
        │
        ▼
safe walk ── nested .gitignore + hard cache skips + no symlinks
        │
        ▼
Python AST + free-path JS/TS top-level chunks (`path::qualname`, content_hash)
        │
        ▼
content-addressed incremental index (tree_hash + INDEXER_VERSION)
        │
        ├── exact symbol locate ───────────────┐
question ── identifier/token overlap          │
        │                                      ▼
        └──────────────────────────── answer or fixed refusal
                                               └── path:start-end citations
optional ── git log/blame on catalog path ─── capability_missing if unavailable
```

## Trust boundary

The HTTP and CLI surfaces accept only catalog ids (`mini`, `production_rag`, `mini_js`); a
request value is never a filesystem path. One function, `validate_repo_id`, backs every
surface. The optional `REPOMIND_CATALOG_PRODUCTION_RAG` setting can replace only the root
behind that existing id for a trusted local operator. Evaluation constructs its catalog with
environment overrides disabled, so CI always scores committed bytes.

The walker never follows symlinks. Hard cache directories stay excluded even if a nested
ignore file tries to negate them. Source is read as text; the snapshot is never imported or
executed. See [ADR 0001](adr/0001-closed-catalog-parse-only.md) and
[ADR 0003](adr/0003-content-addressed-catalog-index.md).

## Retrieval and evidence

Exact unsplit identifiers select only exact qualified or leaf-name definitions. Otherwise,
identifier-aware lexical overlap ranks symbols, paths, and source text with deterministic
tie-breaking. The response renderer can describe only retrieved definitions. No positive
score produces a fixed refusal and zero citations.

`GET /v1/code/symbols` exposes the same chunks as a stable outline. `GET /v1/catalog`
publishes tree hashes. Every HTTP response gets an `x-request-id`; the UI displays it and
the service emits a compact JSON completion log.

## Deliberate limits

- Python AST + free-path JS/TS plumbing; no semantic embeddings or hosted LLM.
- Optional tree-sitter is an extra; default CI never downloads a grammar.
- Memory-only index, content-addressed and incremental on re-ingest.
- Closed demonstration catalog, not arbitrary repository hosting or zip upload.
- Git history is optional and fixture-local; no remotes.
- Lexical dogfood score measures navigation/citation regressions, not general retrieval quality.

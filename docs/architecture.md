# Architecture

RepoMind is a parse-only code navigation service. It turns Python definitions into stable,
line-addressable evidence without executing repository code or calling a model.

```text
closed repo_id catalog
        │
        ▼
safe walk ── nested .gitignore + hard cache skips + no symlinks
        │
        ▼
Python ast.parse ── function/class/method chunks (`path::qualname`)
        │
        ▼
immutable in-memory lexical index
        │
        ├── exact symbol locate ───────────────┐
question ── identifier/token overlap          │
        │                                      ▼
        └──────────────────────────── answer or fixed refusal
                                               └── path:start-end citations
```

## Trust boundary

The HTTP and CLI surfaces accept only `mini` or `production_rag`; a request value is never a
filesystem path. The optional `REPOMIND_CATALOG_PRODUCTION_RAG` setting can replace only the
root behind that existing id for a trusted local operator. Evaluation constructs its catalog
with environment overrides disabled, so CI always scores committed bytes.

The walker never follows symlinks. Hard cache directories stay excluded even if a nested
ignore file tries to negate them. Python input is read as text and passed to `ast.parse`; the
snapshot is never imported or executed. See [ADR 0001](adr/0001-closed-catalog-parse-only.md).

## Retrieval and evidence

Exact unsplit identifiers select only exact qualified or leaf-name definitions. Otherwise,
identifier-aware lexical overlap ranks symbols, paths, and source text with deterministic
tie-breaking. The response renderer can describe only retrieved definitions. No positive
score produces a fixed refusal and zero citations.

`GET /v1/code/symbols` exposes the same chunks as a stable outline. Every HTTP response gets
an `x-request-id`; the UI displays it and the service emits a compact JSON completion log.

## Deliberate limits

- Python only; no semantic embeddings or hosted LLM.
- Memory-only index rebuilt at process start.
- Closed demonstration catalog, not arbitrary repository hosting.
- Lexical dogfood score measures navigation/citation regressions, not general retrieval quality.

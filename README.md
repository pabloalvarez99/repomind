# RepoMind

Repository Q&A with AST-aware Python chunking and path:line citations, designed to run
end to end without API keys, network calls, or billed providers.

> Production-shaped AI systems: free-path demos, real architecture, measurable behavior,
> honest scope.

## Status

| Milestone | Capability | Status |
| --- | --- | --- |
| M0 | Python package, FastAPI health endpoint, tests and CI | LIVE |
| M1 | Repository walk and AST chunks | LIVE |
| M2 | In-memory symbol and token index | LIVE |
| M3 | Code Q&A with path:line citations | PLANNED |
| M4 | JSON CLI | PLANNED |
| M5 | Fixture evaluation harness | PLANNED |

## Try the free path

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn repomind.main:app --port 8020
curl -s http://127.0.0.1:8020/health
```

The default path is deterministic and offline. `.env.example` contains only empty
placeholders; RepoMind does not read them.

## Architecture

```text
repository → safe walk → Python AST chunks → in-memory index
question   → symbol/token retrieval → grounded answer or refusal
                                      └─ path:start_line-end_line citations
```

The fixture proves control flow and citation correctness, not retrieval quality on arbitrary
repositories. Evaluation evidence will be added with M5.

M1 uses gitwildmatch rules from the repository's root `.gitignore`, skips symlinks, and emits
one chunk per Python class, function, async function, and method. A chunk id is
`path::qualname`; its line range comes directly from Python's AST.

M2 indexes those chunks in memory. Exact symbol matches outrank identifier-aware token
overlap across qualified names, paths, and source; deterministic tie-breaking makes results
reproducible. There is no embedding model and no network call in this index.

## License

MIT — see [LICENSE](LICENSE).

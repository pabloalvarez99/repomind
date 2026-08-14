# RepoMind

[![CI](https://github.com/pabloalvarez99/repomind/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/repomind/actions/workflows/ci.yml)

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
| M3 | Code Q&A with path:line citations | LIVE |
| M4 | JSON CLI | LIVE |
| M5 | Fixture evaluation harness | LIVE |

## Try the free path

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn repomind.main:app --port 8020
curl -s http://127.0.0.1:8020/health
curl -s http://127.0.0.1:8020/v1/code/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Where is create_app defined?","repo_id":"mini"}'
```

The default path is deterministic and offline. `.env.example` contains only empty
placeholders; RepoMind does not read them.

Ask from the command line; stdout is exactly one JSON object:

```bash
python -m repomind ask "Where is create_app defined?" --fixture mini
python -m repomind.evals.run
```

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

M3 exposes `POST /v1/code/ask`. Every answer sentence identifies a retrieved definition and
every citation carries its repository-relative path and exact AST line range. No match produces
an explicit refusal with an empty citation list. Repository ids select a fixed catalog; they are
never interpreted as caller-controlled filesystem paths.

M4 and M5 put the same service behind a JSON CLI and a committed 14-question fixture gate.
The gate covers exact symbols, prose retrieval, line citations, refusals, and definitions in
gitignored files. It is a regression check for this fixture—not a claim about arbitrary-repo
answer quality—and reports `judge: null` and `billed_usd: 0.0`.

## License

MIT — see [LICENSE](LICENSE).

# RepoMind

[![CI](https://github.com/pabloalvarez99/repomind/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/repomind/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-c7ff5e.svg)](LICENSE)

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
| M6 | Production RAG snapshot, closed catalog and symbol outline | LIVE |
| M7 | Local ask console, release docs and container | LIVE |

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

Open `http://127.0.0.1:8020/` for the ask console. It shows grounded answers or explicit
refusals, citations as `path:start-end`, and the request correlation id. It uses no CDN.

The default path is deterministic and offline. `.env.example` contains only empty
placeholders; RepoMind does not read them.

Ask from the command line; stdout is exactly one JSON object:

```bash
python -m repomind ask "Where is create_app defined?" --fixture mini
python -m repomind ask "Where is run_query defined?" --repo production_rag
python -m repomind.evals.run
python -m repomind.evals.dogfood
```

## Architecture

```text
repository → safe walk → Python AST chunks → in-memory index
question   → symbol/token retrieval → grounded answer or refusal
                                      └─ path:start_line-end_line citations
```

The committed 14-question mini gate and 8-question Production RAG dogfood gate run offline.
They prove control flow, citation correctness, and refusal behavior on committed bytes—not
retrieval quality on arbitrary repositories. The dogfood suite is a navigation/citation gate
over a small frozen snapshot, not a general code-RAG benchmark. See the
[evaluation contract](data/eval/README.md).

M1 uses hierarchical gitwildmatch rules from every nested `.gitignore`, skips symlinks, and emits
one chunk per Python class, function, async function, and method. A chunk id is
`path::qualname`; its line range comes directly from Python's AST.

M2 indexes those chunks in memory. Exact symbol matches outrank identifier-aware token
overlap across qualified names, paths, and source; deterministic tie-breaking makes results
reproducible. There is no embedding model and no network call in this index.

M3 exposes `POST /v1/code/ask`. Every answer sentence identifies a retrieved definition and
every citation carries its repository-relative path and exact AST line range. No match produces
an explicit refusal with an empty citation list. Repository ids select a fixed catalog; they are
never interpreted as caller-controlled filesystem paths.

M6 adds `GET /v1/code/symbols?repo_id=mini`, which returns a stable AST outline, and a second
catalog id, `production_rag`. That id resolves to a curated snapshot committed here. Local
operators may point the existing id at another read-only root with
`REPOMIND_CATALOG_PRODUCTION_RAG`; evals deliberately ignore the override.

M4 and M5 put the same service behind a JSON CLI and a committed 14-question fixture gate.
The gate covers exact symbols, prose retrieval, line citations, refusals, and definitions in
gitignored files. It is a regression check for this fixture—not a claim about arbitrary-repo
answer quality—and reports `judge: null` and `billed_usd: 0.0`.

## API surface

- `GET /health` — liveness and version.
- `GET /v1/code/symbols?repo_id=mini` — deterministic definition outline.
- `POST /v1/code/ask` — answer or fixed refusal with path:line citations.
- `GET /` and `GET /ask` — local, accessible ask console.

See [architecture](docs/architecture.md), [case study](docs/CASESTUDY.md), and the
[ship checklist](docs/SHIP.md). Security reports and local contributions are covered by
[SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

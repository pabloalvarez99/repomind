# SHIP checklist — v0.2.0

## Product

- [x] One-sentence value prop for hiring managers.
- [x] Free demo path documented first.
- [x] Hosted free path, no clone and no key: <https://pax-repomind.vercel.app>
- [x] Paid path separated: none exists or is required.
- [x] LIVE / DECLARED / PLANNED table in README.
- [x] Former 422 id `production_rag` works on `POST /v1/code/ask` (catalog contract).
- [x] Content-addressed incremental index + `GET /v1/catalog`.
- [x] Free-path JS fixture `mini_js` with path:line golden.
- [x] Optional git history with explicit `capability_missing`.

## Engineering

- [x] `src/` package, `pyproject.toml`, Python 3.12+.
- [x] Offline unit and HTTP integration tests.
- [x] Ruff and strict mypy.
- [x] CI on push and pull request with empty provider keys; no tree-sitter download in default CI.
- [x] ADRs for the catalog/sandbox, lexical baseline, and content-addressed index.
- [x] JSON HTTP completion logs with request correlation id.
- [x] One `validate_repo_id` shared by POST, GET console, symbols, catalog, history, CLI.

## Trust

- [x] No credentials required or committed.
- [x] `SECURITY.md` and `CONTRIBUTING.md`.
- [x] MIT license.
- [x] Eval metrics disclose deterministic provider, null judge, and $0 bill.
- [x] Never accept raw filesystem paths; hosted indexes only committed fixtures.

## Polish

- [x] CI, Python, and license badges.
- [x] P1–P5 portfolio series badge strip.
- [x] Architecture diagram.
- [x] Free-path console covered by live HTTP tests.
- [x] Case study linked above the fold for non-running reviewers.
- [x] Deterministic UI captures committed under `docs/assets`.

## Release evidence

| Evidence | Where | Status |
| --- | --- | --- |
| Mini eval, 14/14 committed cases | `python -m repomind.evals.run` | LIVE |
| Production RAG dogfood, 8/8 snapshot cases | `python -m repomind.evals.dogfood` | LIVE |
| JS fixture golden, foo → path:line | `data/eval/js_questions.jsonl` | LIVE |
| CLI stdout, exactly one JSON object | `python -m repomind ask ...` | LIVE |
| Container, Python 3.12 slim, unprivileged, port 8020 | `Dockerfile` | LIVE |
| Hosted console and API, same fixtures, no key | <https://pax-repomind.vercel.app> | LIVE |
| Hosted POST `production_rag` (former 422) | `POST /v1/code/ask` | LIVE |
| Catalog with tree hashes | `GET /v1/catalog` | LIVE |
| History capability_missing on plain fixtures | `GET /v1/code/history` | LIVE |
| Case study with decisions and eval limits | [`docs/CASESTUDY.md`](CASESTUDY.md) | LIVE |
| UI capture script, asserts outcome before writing | [`scripts/capture_ui.py`](../scripts/capture_ui.py) | LIVE |
| Console capture, mini exact-symbol hit with `path:start-end` | `docs/assets/ui-mini-hit.png` | LIVE |
| Console capture, mini refusal with zero citations | `docs/assets/ui-mini-refuse.png` | LIVE |
| Console capture, `production_rag` snapshot hit | `docs/assets/ui-dogfood-hit.png` | LIVE |
| Capture staleness gate, capture and source hashes checked on every CI run | `tests/test_capture_assets.py` | LIVE |

Capture rows are LIVE only while `scripts/capture_ui.py` and all three PNGs are committed. The
script pins the correlation id and nothing else, so an unchanged tree reproduces identical
bytes; a changed console requires regenerating the PNGs in the same commit.

CI keeps those rows honest without a browser. `docs/assets/ui-captures.sha256` records one
sha256 per committed PNG and `docs/assets/ui-sources.sha256` records one per file that decides
what a capture shows, so `tests/test_capture_assets.py` fails when a documented image is
missing, when a referenced PNG has no hash, when the committed bytes drift, or when the
template, stylesheet, or console script changed without new captures. Regenerating
captures is a local step; verifying them is not.

# HONESTY — RepoMind v1.0.0 lock

**Agent:** A3 · **Repo:** `pabloalvarez99/repomind` · **Baseline main:** `099ac8a` · **Host:** https://pax-repomind.vercel.app  
**Law:** prove every release claim with a command + observed result, or **STRIKE**. No new languages, no live scrape, no zip upload, no SOTA claims.

| # | Claim (release / season) | Command | Expected | Observed | Verdict |
|---|--------------------------|---------|----------|----------|---------|
| 1 | Host health version 1.0.0 | `GET https://pax-repomind.vercel.app/health` | `version":"1.0.0"` | `{"status":"ok","service":"repomind","version":"1.0.0"}` | **PASS** |
| 2 | Catalog lists fixtures + pin fields | `GET /v1/catalog` | mini, mini_js, production_rag; `source_sha`, `indexer_version` | All three present; `indexer_version=3` | **PASS** |
| 3 | Dogfood pin is current P1 (not stale bf6e36d) | pin file + catalog after refresh/deploy | `source_sha=3b54d85a9c0d3ba85bd0760058aafce76849d1f7` | Fixture + local + hosted catalog all `3b54d85…` | **PASS** |
| 3b | Hosted catalog shows new pin after deploy | `GET /v1/catalog` post-deploy | production_rag `source_sha` = `3b54d85…` | `source_sha=3b54d85a9c0d3ba85bd0760058aafce76849d1f7` · tree `d36881b6…` · chunks 63 | **PASS** |
| 4 | POST ask production_rag path:line | `POST /v1/code/ask` `run_query` | citation `production_rag/query_pipeline.py:244-277` | 200 · `244-277` (local + pre-deploy host) | **PASS** |
| 5 | History 200 from snapshot (no git) | `GET /v1/code/history?repo_id=mini&path=app/main.py&mode=log` | 200 + entry sha | 200 · sha `93afe12c…` · summary committed fixture history | **PASS** |
| 6 | Refs 200 who-calls | `GET /v1/code/refs?repo_id=mini&symbol=create_app` | callers include boot @ app/main.py:19 | 200 · `boot` @ `app/main.py:19` | **PASS** |
| 7 | Program eval n≥50 | `evaluate_program()` / `pytest tests/test_program_difficulty.py` | n≥50, failed=0 | **n=52** passed=52 failed=0 | **PASS** |
| 8 | Difficulty predicates fail all-rank-1 stress slice | `test_difficulty_rejects_all_easy_stress_slice` | failures mention trivial/rank-1 | 4/4 program difficulty tests green; planted slice fails | **PASS** (in default pytest CI) |
| 9 | Mini + dogfood + js free-path evals | `python -m repomind.evals.run` + dogfood + js | 0 failed | mini 14/14 · dogfood 8/8 · program 52/52 | **PASS** |
| 10 | Pack/unpack round-trip billed $0 | pack_catalog + unpack_catalog | billed_usd 0 · repos present | billed_usd 0.0 · mini/mini_js/production_rag | **PASS** |
| 11 | Load 200 mini asks vs committed load.json | `python scripts/load_mini_asks.py` | delta p50/p95 ≤ 3× or explain | committed p50=0.481 p95=0.745 → re-run p50=0.412 p95=0.666 (ratios ~0.86× / 0.89×) | **PASS** |
| 12 | Default CI never downloads tree-sitter | inspect `.github/workflows/ci.yml` + pyproject | only `pip install -e ".[dev]"`; treesitter optional | Confirmed: no treesitter in CI; optional extra + importorskip | **PASS** |
| 13 | Language packs python-ast / js / json | unit tests + INDEXER_VERSION 3 | three free packs, no network | `test_three_free_path_packs_registered_without_network` PASS | **PASS** |
| 14 | Rename-aware history goldens | program slice rename/history | green | in program 52/52 | **PASS** |
| 15 | includeFiles stays | `vercel.json` | `{src/**,fixtures/**}` | present | **PASS** |
| 16 | No raw path as repo selector | API tests / catalog | 400/422 on path-shaped ids | CI + unit tests cover | **PASS** |
| 17 | CASESTUDY ≥1500 words | word count CASESTUDY.md | ≥1500 | **1781** words | **PASS** |
| 18 | Incremental no-op on dogfood pin | second ingest is_noop | true | `test_production_rag_pin_is_current_and_noop_on_second_ingest` PASS | **PASS** |
| 19 | Not SOTA / not live git / no uploads | release notes PLANNED | honest PLANNED list | unchanged PLANNED: no live git, no uploads, no required tree-sitter, not semantic SOTA | **PASS** (documented, not claimed) |
| 20 | Full pytest suite green | `pytest -q` | all free-path tests pass | **132 passed, 1 skipped** | **PASS** |

## Hosted transcripts (pre-refresh deploy baseline)

```
GET /health
{"status":"ok","service":"repomind","version":"1.0.0"}

GET /v1/catalog  (pre-deploy pin still bf6e36d — honesty gap that this lock fixes)
production_rag source_sha=bf6e36d1d4ca353c4f17f649cb721da51d74f6bb indexer_version=3

POST /v1/code/ask {"question":"Where is run_query defined?","repo_id":"production_rag"}
200 · production_rag/query_pipeline.py:244-277

GET /v1/code/history?repo_id=mini&path=app/main.py&mode=log
200 · entries[0].sha=93afe12c1e8baae2e5050fa13e028a5d5aeedc7b

GET /v1/code/refs?repo_id=mini&symbol=create_app
200 · callers[0]=boot @ app/main.py:19
```

## Snapshot refresh (lock fix)

| Field | Before (v1.0.0 ship) | After (this lock) |
|-------|----------------------|-------------------|
| `source_sha` | `bf6e36d1d4ca353c4f17f649cb721da51d74f6bb` | `3b54d85a9c0d3ba85bd0760058aafce76849d1f7` |
| Upstream | P1 v0.3.0 family | P1 v1.0.0 main |
| Selected paths | same six `src/production_rag/...` files | same |
| Content delta | — | only `api/routes/query.py` gained filter/cache helpers; other five blobs identical; `run_query` still **244-277** |
| Goldens | path+symbol | retarget not required (no line expectations); pin asserts updated |
| History | regenerated for production_rag | `.repomind/history.jsonl` rewritten |

## Load delta detail

| Metric | Committed `docs/assets/load.json` | Re-run (this session) | Ratio |
|--------|-----------------------------------|------------------------|-------|
| n | 200 | 200 | 1.0 |
| answered/refused | 175/25 | 175/25 | 1.0 |
| p50_ms | 0.481 | 0.412 | 0.86× |
| p95_ms | 0.745 | 0.666 | 0.89× |

No explanation required for >3× (none exceeded). Faster numbers are machine noise on a lexical fixture, not a capacity claim. Committed file updated to this re-run.

## Strikes / PLANNED (honest non-claims)

| Item | Status |
|------|--------|
| Live git history on Vercel | **STRIKE as product claim** — snapshots only (PLANNED forever under serverless) |
| Stranger zip / raw path upload | **STRIKE as product claim** — closed catalog |
| tree-sitter required in CI | **STRIKE as product claim** — optional extra only |
| Semantic / SOTA code search | **STRIKE as quality claim** — free path is deterministic lexical + AST structure |

## Counts

- **PASS:** 20 (all claim rows including hosted pin)
- **FAIL:** 0
- **STRIKE (as overclaim):** 4 PLANNED non-goals kept honest
- **Blocked:** none

## Ship surface

| Item | Value |
|------|--------|
| Branch | `a3/p4-v1-lock` → PR #7 merged |
| main | `91fa395` |
| CI main | run `31851045112` success |
| Host | https://pax-repomind.vercel.app @1.0.0 |
| Release | v1.0.0 (no retag; lock is honesty refresh) |

## Post-deploy host transcripts

```
GET /health
{"status":"ok","service":"repomind","version":"1.0.0"}

GET /v1/catalog production_rag
source_sha=3b54d85a9c0d3ba85bd0760058aafce76849d1f7
indexer_version=3
tree_hash=d36881b65e5c00e74eec056b597f3119c51066473e99cd25dfa1a98d540acb25
chunk_count=63

POST /v1/code/ask {"question":"Where is run_query defined?","repo_id":"production_rag"}
200 · production_rag/query_pipeline.py:244-277

GET /v1/code/history?repo_id=mini&path=app/main.py&mode=log
200 · entries[0].sha=93afe12c1e8baae2e5050fa13e028a5d5aeedc7b

GET /v1/code/refs?repo_id=mini&symbol=create_app
200 · callers[0]=boot @ app/main.py:19
```

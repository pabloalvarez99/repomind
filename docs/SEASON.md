# Season plan — repomind → v1.0.0 (90 days)

**Owner:** A3 (this repository only).  
**Horizon:** one quarter, not one afternoon.  
**Baseline:** `main@4de0ac6` · Release **v0.3.0** · host https://pax-repomind.vercel.app · history snapshots **200** (no git on host) · who-calls refs · JS fixture · `production_rag` pin still **`d43f812`** (ancestor of P1 v0.3 `bf6e36d`).  
**Law:** Month 1 week 1 is **design only** (this file). `REPORTE … OK` is illegal before the Month 3 gate. Do not retag v0.3.0 as v1.0.0. Do not treat a snapshot SHA bump as season completion.

Authoritative references: master plan **§9** (P4 mission / AST / path:line), **§12** (eval doctrine — Tier1 free), **§30.8** (code intelligence catalog: `ast`, walker, path:line, fixtures, optional git log), **§39** (tree-sitter as stretch — richer languages, never a default-CI download). Supporting ADRs: 0001 closed catalog, 0002 deterministic lexical baseline, 0003 content-addressed index, 0004 committed history snapshots.

---

## 0. What this season is (and is not)

### Threat model for the hiring manager

A staff engineer will open this repo and ask:

1. Can I ask “where is X?” with **empty keys** and get a **path:line** citation on a fixture?
2. Does the host accept **only catalog ids**, or can I smuggle a raw filesystem path?
3. Is “history” **git(1) on a serverless box**, or a **committed snapshot** with an honest 503 when missing?
4. Are the eval numbers a **measurement program** (n, slices, difficulty predicates), or 14 easy symbol lookups with a quality caption?
5. When languages expand, does default CI **download grammars from the network**, or stay offline on vendored / stdlib parsers?

v0.3.0 already answers (1)–(3) on the free path and host: closed catalog, incremental hashes, history snapshots (200), who-calls refs, JS fixture, `includeFiles` for Vercel. It does **not** yet ship a free-path evaluation *program* with **n ≥ 50** and mechanical difficulty predicates, a current P1 snapshot at or past `bf6e36d`, a language-**pack** product surface, rename-aware history goldens, or an offline **pack/unpack** round-trip.

### Non-goals (entire season)

| Non-goal | Why |
| --- | --- |
| Stranger uploads / raw path indexing | Sandbox: closed allowlist only (§13 #4, ADR-0001) |
| Live GitHub scrape or live clone of production-rag | Hosted indexes **committed fixtures only**; dogfood is a pin with `source_sha` |
| Dropping `includeFiles: {src/**,fixtures/**}` | Hosted Jinja + fixture roots break without it |
| tree-sitter as a **required** CI dependency | §39 stretch; free path must stay network-free |
| Claiming SOTA code search / semantic retrieval quality | Free path is **lexical + AST structure**; labels must say so |
| Server-side durable git(1) on Vercel | ADR-0004: snapshot first; no git binary theater |
| Subagents / multi-repo edits | A3 owns `repomind` only |
| Reporting season OK in Month 1 | Brief law |

### Season deliverables (high level)

| Month | Product surface | Evidence a stranger can run |
| --- | --- | --- |
| **1** | Eval program **n ≥ 50** with slices + **difficulty predicates**; refresh `production_rag` from P1 `bf6e36d` (or newer) with recorded `source_sha`; first 25 goldens under predicates; hosted POST ask + GET history 200 + GET refs transcripts | `pytest` fails if a slice is all trivial; digest HTTP transcripts; pin in `.repomind/source.json` |
| **2** | Language-pack interface: **python-ast** (default), **js** (existing extra path), **one more vendored** language/config pack; rename-aware history (old_path→new_path); UI shows indexer_version, tree hash, source SHA; ADR on packs / no live git / no zip upload | Goldens per pack; total n ≥ 50; capture of catalog metadata |
| **3** | `repomind pack` / `unpack` offline artifact; load/soak 200 asks on mini (p50/p95, honesty caption); CASESTUDY ≥1500 words season trade-offs; DEMO 15 min; **v1.0.0** only if checklist green | Pack round-trip tests `billed_usd: 0`; load JSON; release notes list PLANNED |

---

## 1. Fifteen invariants

Each invariant is **normative**. Column **Tested today** is the state on `4de0ac6`. Month 1–3 work may add tests; it must not weaken these.

| # | Invariant | Meaning | Source | Tested today (v0.3.0) |
| --- | --- | --- | --- | --- |
| I1 | **Closed catalog allowlist** | Only known `repo_id` values resolve to roots. Unknown well-formed ids → typed unknown; path-shaped / empty ids → malformed. Environment may override **root for `production_rag` only**, never add ids. | ADR-0001, §13 | **yes** — `tests/test_catalog.py`, API 4xx |
| I2 | **No raw path input** | HTTP/CLI never accept a filesystem path as the repository selector. Questions and history take `repo_id` + relative `path` under that root. | ADR-0001 | **yes** |
| I3 | **Hosted = committed fixtures only** | Production host indexes packaged fixtures under `fixtures/`. No stranger upload, no open directory browser. | Mission, SHIP | **yes** (deploy surface); keep `includeFiles` |
| I4 | **History prefers snapshot** | When `.repomind/history.jsonl` exists for a catalog root, answers come from it. Hosted fixtures **must** ship snapshots so public history is **200**, not git theater. | ADR-0004 | **yes** — snapshot + host 200 |
| I5 | **History without snapshot is capability-honest** | No snapshot and no usable local git → **503** `capability_missing` (not empty 200, not fake commits). Unknown path → 404; escape → 400. | ADR-0004 | **yes** |
| I6 | **path:line citations** | Answerable hits cite repository-relative path and line range from chunks, not free-floating prose. | §9.4, §11.2 | **yes** — evals + API tests |
| I7 | **Refuse over invent** | Unanswerable / no-hit cases return refusal without citations (`expect_refusal` / empty cites). | free-path ethics, §12 Tier1 | **yes** — mini + dogfood refuse cases |
| I8 | **AST (or declared pack) chunks, not only whole-file bags** | Python free path uses `ast`-aligned chunks (`chunk_id` / qualname / kind / lines). JS uses the pure scanner unless optional tree-sitter is installed. | §9, §30.8 | **yes** for py+js scanners |
| I9 | **Incremental content-addressed index** | Unchanged files are no-ops; a single file change reindexes that parse unit. Catalog exposes content/tree identity fields the UI can show. | ADR-0003 | **yes** — incremental tests; UI fields grow in M2 |
| I10 | **Refs are plumbing, not SOTA** | Incoming who-calls lists plain Name/Attribute call sites from the AST walker. Empty list means **leaf**, not “unknown.” Docs must not claim full call-graph precision across dynamics. | v0.3 who-calls | **yes** — unit + golden create_app→boot |
| I11 | **Free-path billed $0** | Eval JSON: `judge: null`, `billed_usd: 0.0`, provider `deterministic-lexical` (or pack-local). No paid model judge in default CI. | §12 Tier1 | **yes** |
| I12 | **Difficulty predicates on program slices** | A program slice that is all trivial (e.g. every answerable item is exact-symbol rank-1 under the baseline the slice claims to stress) **fails CI**. Labels alone are not enough. | §12; P1 deep_rank lesson | **no** — **Month 1 weeks 2–4** |
| I13 | **Default CI never downloads grammars** | `[treesitter]` remains optional + `pytest.importorskip` / marker. Default workflow does not `pip install` network grammars. Third language pack must be **vendored or stdlib**. | §39, pyproject | **yes** today; **must hold** when packs land |
| I14 | **Dogfood pin is recorded** | `production_rag` ships `.repomind/source.json` with `source_sha`, upstream, path selection. Catalog/UI expose `source_sha`. Refresh does not silently drop the pin. | v0.3 dogfood | **yes** (pin present; **stale vs P1 v0.3** — M1 refresh) |
| I15 | **includeFiles stays** | `vercel.json` continues to ship `src/**` and `fixtures/**` (and any future pack assets under those trees). Removing it is a regression. | deploy gotcha | **yes** (config); guard in docs/tests as needed |

**Operational gotcha (not a numbered invariant):** `POST /v1/code/ask` historically rejected underscores in some gate layers while catalog ids use `production_rag`. The closed catalog and API must stay aligned so dogfood works on the same id as `GET /ask` and symbols/refs. Do not reintroduce a stricter regex than `catalog.validate_repo_id`.

---

## 2. Month 1 — eval program + current snapshot

### Week 1 (this commit) — DESIGN ONLY

Deliverable: **this file**. No new golden rows, no snapshot refresh, no pack interface code, no release. Commit and stop implementing Month 1 features in the same change as this design.

### Baseline inventory (do not re-litigate)

| Artifact | n / shape | Role |
| --- | --- | --- |
| `data/eval/code_questions.jsonl` | **14** (10 answerable + 4 refuse) · `mini` | Fast regression gate, not the season program |
| `data/eval/dogfood_questions.jsonl` | **8** (locate/cite + refuse) · `production_rag` @ `d43f812` | Pin navigation gate; must be **retargeted** after snapshot refresh |
| `data/eval/js_questions.jsonl` | **4** · `mini_js` | JS free-path smoke (pure scanner) |
| **Total today** | **26** | Below season **n ≥ 50**; no difficulty predicates |
| History snapshots | `fixtures/*/.repomind/history.jsonl` | Hosted history **200** |
| Refs | Python AST callers | Plumbing; not full CG |
| Optional tree-sitter | `[project.optional-dependencies].treesitter` | Skipped in default CI |

Interpretation already written in `data/eval/README.md`: perfect scores on these sets prove **fixture navigation**, not retrieval quality on arbitrary repos. Month 1 keeps that honesty while **growing a program set**.

### Free-path program set (n ≥ 50) — definition

**Program set** means:

- Runnable with empty keys, no network, deterministic lexical (+ AST structure) stack.
- Committed JSONL under `data/eval/` (one file or a small family with a single runner entrypoint).
- **n ≥ 50** scored items after excluding pure schema-only fixtures if any appear later.
- Every item has: stable `id`, `question`, `repo_id` (or fixed file defaults), answerability / `expect_refusal`, expected **path** (and symbol/line where applicable), **`slice`** (category), and a short note of **which behaviour** it catches.
- Summary JSON always includes `billed_usd: 0.0` and no model judge.

**Composition targets (across mini / mini_js / production_rag):**

| Slice id | Intent | Target share (≈) | Notes |
| --- | --- | --- | --- |
| `symbol-easy` | exact or near-exact symbol locate | ≤ 30% of program | regression core; **capped** so it cannot dominate |
| `cross-file` | definition and use live in different files; citation must land on the **definition** (or documented dual cite) | ≥ 15% | needs multi-file fixtures |
| `rename/history` | history or rename map answers “where did X go?” / log for a path | ≥ 10% | may be thin in M1 until M2 rename maps; M1 can start with snapshot log/blame goldens |
| `unanswerable` | refuse with no citations | ≥ 15% | off-topic + gitignored/generated + missing symbol |
| `js-symbol` | mini_js locate via free-path JS scanner | ≥ 8% | grows with pack honesty labels |
| `dogfood-locate` | production_rag pin paths still path:line after refresh | ≥ 10% | retarget after SHA refresh |

Do **not** pad with twenty clones of “Where is create_app defined?” to hit n≥50. n is necessary, not sufficient.

**First milestone inside Month 1 (weeks 2–4):** at least **25** program items under predicates + full snapshot refresh, then grow to **≥ 50** before Month 1 exit. Season checklist still requires n≥50.

### Difficulty predicates (mechanical)

A **difficulty predicate** is a pure check CI runs. Failure names the slice and the trivial ids.

| Slice | Predicate (Month 1 implement) | Fails when |
| --- | --- | --- |
| `symbol-easy` | **Quota**, not hardness: count of program items in this slice ≤ **ceil(0.30 × n)** | easy items exceed the cap (padding to pass n) |
| `cross-file` | Expected definition path ≠ path of a committed “surface mention” fixture file (or structured field `mention_path` ≠ `expected_path`), and both paths exist in the fixture tree | all “cross-file” items are single-file exact matches |
| `rename/history` | Item requires history API or rename map fields (`old_path`/`new_path` in snapshot metadata); expected answer path is the **current** path | history items that only re-ask symbol locate without reading history/rename |
| `unanswerable` | `expect_refusal` / no expected path **and** question shares ≥1 identifier-like token with an indexed symbol **or** is explicitly off-corpus | refuse cases that never stress retrieval (empty questions, pure noise) without a documented reason |
| `js-symbol` | `repo_id=mini_js` and expected path ends in `.js`/`.ts` as committed | Python paths smuggled into the JS slice |
| `dogfood-locate` | `repo_id=production_rag` and expected path exists under the **current** snapshot tree; runner loads pin `source_sha` and records it in the report | paths that only existed on the old pin; missing source_sha |

**Hard rule:** if any slice fails its predicate, the integrity job exits non-zero even if every golden “passes” the ask runner.  
**Hard rule:** free-path reports remain **plumbing / navigation** claims, not quality SOTA (§12 Tier1).

### Snapshot refresh plan (weeks 2–4 — not this commit)

1. Read P1 `origin/main` (target **≥ `bf6e36d`**). Record full SHA in `fixtures/production_rag/.repomind/source.json`.
2. Copy only the **selected `src/` paths** (same honesty as today: curated snapshot, not a full monorepo mirror). Update NOTICE if present.
3. Regenerate content-addressed index artifacts as the existing incremental pipeline expects.
4. Regenerate history snapshots for the fixture if paths changed (`scripts/generate_history_snapshots.py`).
5. Retarget dogfood goldens **honestly** (line ranges move — fix expectations, do not weaken to `pass` on any path).
6. Tests: unchanged tree → incremental no-op; one file edit → single reparse (already present — re-verify on new pin).
7. Hosted digest after deploy: POST ask on production_rag, GET history 200, GET refs, catalog `source_sha`.

If P1 main moves again mid-month, prefer **one deliberate pin per Month 1 exit**, not daily churn. Catalog always shows the pin that is committed.

### What Month 1 measures (and publishes)

| Artifact | Contents | Allowed claim |
| --- | --- | --- |
| Eval summary JSON | total/passed/failed, `billed_usd: 0`, provider id, per-slice counts, `source_sha` for dogfood | navigation / regression program |
| Difficulty report | slice → pass/fail predicates | label integrity |
| Hosted transcripts | POST ask (mini + production_rag), GET history 200, GET refs | contract demos |
| Incremental tests | no-op + single-file reparse on refreshed pin | index honesty |

### What Month 1 does **not** measure

- Semantic / embedding code search quality.
- Full call-graph soundness under dynamic dispatch.
- GitHub-scale latency (Month 3 load is **mini**, honest caption).
- Language pack product surface (Month 2).
- Offline pack/unpack (Month 3).
- Live git history as a hosted feature.

### Month 1 weeks 2–4 — build sequence (after this design commit)

1. **Difficulty module + tests** — predicates above; wire into eval entrypoint or `tests/test_evals.py` / a dedicated integrity test.
2. **Grow program set to ≥25 with slices**, then to **≥50** without easy-slice overflow.
3. **Refresh production_rag pin** from P1 ≥ `bf6e36d`; retarget dogfood; incremental checks.
4. **Hosted transcripts** after deploy (or local ASGI if deploy blocked — note which).
5. **Digest append** in second brain; no Month 2 pack code required for Month 1 exit.

**Month 1 exit (not season OK):** predicates green; n≥50 program; pin current; transcripts; free-path CI green. Still no v1.0.0 tag.

---

## 3. Month 2 — language packs + rename-aware history (PLANNED)

Design only here; implement after Month 1 exit.

1. **Pack interface**  
   - `python-ast` — default free path (stdlib `ast`).  
   - `js` — existing pure scanner; optional tree-sitter remains **extra**, skipped in default CI.  
   - **One more** pack: prefer a **vendored** grammar or stdlib/config parser (e.g. JSON/TOML structure pack, or a tiny vendored tree-sitter wasm/grammar **checked into the repo**). Network install in default CI is forbidden (I13).  
   - Each pack declares: id, file globs, chunker entry, honesty label (“structural / lexical, not semantic”).

2. **Goldens per pack** — grow program set so each pack has a non-empty slice; total n ≥ 50 remains the floor.

3. **Rename-aware history**  
   - Snapshot schema gains `old_path` → `new_path` (or equivalent rename records).  
   - Golden: “where did X go?” → **new** path:line.  
   - Hosted still reads committed snapshots only.

4. **UI / catalog** — show `indexer_version`, tree/content hash, `source_sha` for production_rag. Capture regenerated under existing hash gates.

5. **ADR** — why packs; why no live git on host; why no zip upload from strangers.

---

## 4. Month 3 — offline pack + v1.0 (PLANNED)

1. **`repomind pack`** emits directory or tarball: fixtures + index + history snapshots (+ pack manifests). **`repomind unpack`** loads it for local use. Hosted continues to use the **committed** copy; pack is an offline lab artifact.
2. **Tests:** pack round-trip; eval summary still `billed_usd: 0`.
3. **Load/soak:** 200 asks against **mini** locally; publish p50/p95; caption: *lexical fixture, not GitHub-scale* (§39 honesty).
4. **CASESTUDY** ≥1500 words: catalog sandbox, snapshot history vs git, packs vs tree-sitter-in-CI, eval difficulty lesson, why no uploads.
5. **DEMO hosted 15 min:** ask `create_app`, history, refs, unanswerable refuse.
6. **`gh release` v1.0.0** only if checklist green. Latest = v1.0.0. Notes list PLANNED (no live git host, no stranger upload, no required tree-sitter, no semantic SOTA).

---

## 5. v1.0.0 checklist (season gate)

- [ ] This file (`docs/SEASON.md`) lists ≥15 invariants and which have tests.
- [ ] Free-path eval program **n ≥ 50** with difficulty predicates; trivial / over-easy slices fail CI.
- [ ] `production_rag` pin ≥ P1 v0.3 baseline (`bf6e36d` or newer) with recorded `source_sha`.
- [ ] Language packs: python-ast default, js, one more **without** network in default CI.
- [ ] Rename-aware history golden path green.
- [ ] Offline pack/unpack round-trip; hosted still fixtures-only; `includeFiles` present.
- [ ] Load artifact: 200 mini asks, p50/p95, honesty caption.
- [ ] Failure / refuse / capability transcripts (not only happy path).
- [ ] CASESTUDY ≥1500 words with real trade-offs; no invented SOTA.
- [ ] CI green on `main` with empty keys / no grammar download.
- [ ] Release notes state remaining PLANNED items.

---

## 6. DEMO-DAY beats owned by P4 (season end)

| Beat | Proof |
| --- | --- |
| path:line ask on mini | `create_app` → `app/main.py:…` |
| Dogfood pin | production_rag ask after refresh; catalog shows source SHA |
| History snapshot | GET history **200** on fixture path; no git binary claim |
| Who-calls | refs for `create_app` non-empty; leaf empty list honest |
| Unanswerable refuse | no citations |
| JS free path | mini_js symbol without tree-sitter install |
| Pack/unpack (M3) | offline round-trip demo |
| Difficulty honesty | open eval README + predicate failure mode in docs |

---

## 7. Week 1 stop line

This document is the **only** Month 1 week 1 deliverable.

**Do not** in the same change: refresh the P1 snapshot, grow golden JSONL, implement language packs, add rename maps, implement pack/unpack, retag releases, or report season OK.

Next concrete commit theme after this design lands:  
`test(eval): difficulty predicates reject all-easy program slices`  
then grow the program set and refresh `production_rag` from P1 ≥ `bf6e36d` with honest dogfood retargets.

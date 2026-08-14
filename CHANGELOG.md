# Changelog

## v0.2.0 — 2026-08-14

### Fixed

- `POST /v1/code/ask` accepts `production_rag`. The request schema validated `repo_id` against
  `^[a-z0-9-]+$`, a slug shape that rejected an id the catalog itself publishes, so the JSON API
  returned 422 for a repository the browser console answered happily. Validity is now one
  function, `repomind.catalog.validate_repo_id`, whose allowlist is derived from
  `catalog_roots()` — the ids callers may send cannot drift from the ids the service can serve.

### Added

- Content-addressed ingest. Every chunk carries a `content_hash` over its kind, qualified name,
  and source text; every visible file a blob hash; every repository a `tree_hash` folded from the
  sorted `(path, blob_hash)` pairs and the `INDEXER_VERSION` that read them. Sources are
  hashed after CRLF normalization so one commit advertises one index on every platform.
- Incremental re-ingest. `IncrementalIngestor` reuses chunks whose bytes are unchanged, so
  re-ingesting an unchanged repository parses zero files and an edit costs one parse rather than
  a repository. Reuse is decided by content, not by a timestamp.
- `GET /v1/catalog` and `CodeAskService.catalog()` publish `repo_id`, file count, indexed file
  count, chunk count, tree hash, and indexer version. The route takes no arguments: the answer to
  "what can I ask about" is not also a place to name something the catalog does not hold.
- `CodeAskService.reindex(repo_id=...)` re-ingests one catalog repository and reports what the
  ingest actually did.
- ADR 0003 records why the way in is a catalog id, why the tree is hashed, and why the hosted
  instance will not accept a stranger's zip.
- Free-path JavaScript/TypeScript catalog id `mini_js` with a pure scanner (no tree-sitter in
  default CI). Optional extra `[treesitter]` is documented and skipped unless installed.
  Golden: `Where is foo defined?` → `src/foo.js` path:line. Plumbing on a fixture, not SOTA.
- Optional `GET /v1/code/history` for read-only `git log` / `git blame` on a catalog-relative
  path. Missing git or a non-git fixture root returns `503` with
  `detail=capability_missing`. No remotes, no upload, no arbitrary paths.

### Changed

- `POST /v1/code/ask`, `GET /ask`, `GET /v1/code/symbols`, `GET /v1/catalog`,
  `GET /v1/code/history`, and the CLI share the one validity function and therefore agree on
  every id. Blank is 422, path-shaped is 400, well-formed-but-absent is 404; the CLI exits 2 and
  names the known ids on stderr.
- `INDEXER_VERSION` is now `2` (JS/TS top-level definitions enter the index).
- Hosted free path at <https://pax-repomind.vercel.app>: a root `main.py` re-exports
  `repomind.main:app`, and `vercel.json` builds it with `@vercel/python`, including `src/`
  and `fixtures/` so the closed catalog resolves inside the function. The hosted instance
  answers over the same committed fixtures as the local path — no key, no clone, no
  embeddings, and no claim beyond those fixtures.
- `scripts/capture_ui.py` regenerates three deterministic console screenshots and asserts the
  rendered outcome before writing each PNG. Playwright lives in a new optional `docs` extra and
  stays out of CI.
- Committed `docs/assets/ui-mini-hit.png`, `ui-mini-refuse.png`, and `ui-dogfood-hit.png` so a
  reviewer can see a `path:start-end` citation without running the server.
- `docs/assets/ui-captures.sha256` plus `tests/test_capture_assets.py` close the stale-evidence
  hole: every image published by the README, SHIP, or case study must exist, must be hashed, and
  must match its recorded sha256. CI checks hashes only, so no browser is downloaded.
- `docs/assets/ui-sources.sha256` plus `scripts/hash_ui_assets.py` finish that gate: the template,
  stylesheet, console script, and capture script are hashed too, so a CSS or HTML change fails CI
  until the captures are regenerated. Unchanged PNG bytes no longer read as fresh evidence.
- Console citations carry a copy button for their `path:start-end`, shipped hidden and revealed
  by a local script so a browser without JavaScript never shows a dead control. Captures and
  hashes regenerated in the same commit.
- Case study rewritten around four decisions and an explicit account of what the 14/14 and 8/8
  scores do and do not prove; linked above the fold in the README.
- P1–P5 portfolio series badge strip; SHIP release evidence is now a LIVE-status table.

## v0.1.0 — 2026-08-14

- Parse-only Python AST chunks with stable `path::qualname` ids and line ranges.
- Deterministic exact-symbol and lexical navigation with grounded refusal behavior.
- Closed mini and Production RAG snapshot catalogs; no caller filesystem paths.
- JSON ask API, deterministic symbol outline, one-object CLI, and local ask console.
- Hierarchical `.gitignore`, symlink/cache exclusion, 14 mini and 8 dogfood evals.
- Python 3.12 container and credential-free CI across lint, types, tests, evals, CLI, and HTTP.

The dogfood score is a locate-and-cite regression gate over committed snapshot bytes. It is not
a claim of arbitrary-repository retrieval quality or code-RAG SOTA.

# Changelog

## Unreleased

- Documentation only; no runtime, API, or eval behavior changed.
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

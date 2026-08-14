# ADR 0004: Committed history snapshots on serverless

Status: accepted.

## Context

`GET /v1/code/history` was implemented as a thin wrapper around local `git log`
and `git blame`. That is honest on a developer laptop that has `git(1)` and a
real work tree. It is dishonest on the hosted free path:

1. The Vercel Python image does not ship `git`.
2. Catalog fixtures are not stand-alone git repositories; they are directories
   inside the product tree. Even with git present, `rev-parse --show-toplevel`
   points at the product repo, and answering with *those* commits would leak
   product history as if it belonged to the fixture.
3. A hiring manager who clicks History and gets `503 capability_missing` on
   every fixture path correctly reads that as a fake surface.

Documenting the 503 is not a fix. The product either answers fixture history
without git, or it must stop advertising the endpoint.

## Decision

### Snapshots are the production path

Each catalog fixture commits a deterministic table at
`.repomind/history.jsonl`, produced by
`scripts/generate_history_snapshots.py`. Runtime history for packaged fixtures
reads only that file. The request path never shells out to git for those roots.

Rows are content-addressed: a 40-hex id derived from path + normalized file
bytes, one log entry, and blame rows for non-empty lines. Same fixture bytes
always produce the same snapshot. Re-running the script after editing fixture
source is a deliberate, reviewable change — not a live clone of GitHub.

### Git stays as an optional local fallback

When a catalog root has **no** snapshot (for example
`REPOMIND_CATALOG_PRODUCTION_RAG` pointing at a local worktree), the service may
still run read-only `git log` / `git blame` if the root is itself a git toplevel.
That path never runs on the hosted free path and never accepts a remote URL.

### Status codes stay explicit

| Situation | Status |
| --- | --- |
| Snapshot present, path is a fixture file with rows | `200` |
| Path escapes the catalog root or is absolute | `400` |
| Path is well-formed but names no file | `404` |
| No snapshot and no usable local git | `503 capability_missing` |
| Snapshot present but path was not recorded | `503 capability_missing` |

Empty success is never used to hide a missing capability.

## Consequences

- Hosted History on `mini`, `mini_js`, and `production_rag` returns `200` without
  git in the image.
- Fixture history is a **committed claim** about the snapshot, not live VCS
  history and not a claim that we index GitHub.
- Stale snapshots after fixture edits are a real failure mode; the generator
  supports `--check` so CI or a pre-commit step can catch drift.
- Callers that need true multi-commit git history must run locally against a
  real git root (or wait for a product that stores remotes — out of scope).

## Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Bundle `git` in the Vercel image | Still fails: fixtures are not stand-alone repos; packaging `.git` is large, fragile, and would still be product-repo history if nested. |
| Answer with product-repo commits | Lies about which repository the path belongs to. |
| Remove the endpoint | Honest, but drops a useful free-path demo for path-level provenance once we have snapshots. |
| Live clone of GitHub on request | Violates the closed catalog, needs network and credentials, and is not the product. |

# ADR 0003: Content-addressed catalog index

Status: accepted.

## Context

Three questions kept having no mechanical answer. Did the index change? Is this deployment
serving the same bytes as that one? Why re-parse a snapshot that nobody edited?

`CodeAskService.from_roots` used to chunk every visible Python file on every construction, and
the result carried no identity beyond "whatever was on disk at import time". Two instances could
disagree and neither could say so.

## Decision

### Catalog ids, not paths, are the way in

A `repo_id` is an identifier `catalog_roots()` hands out. `repomind.catalog.validate_repo_id`
is the one place that decides validity, and its allowlist is *derived* from `catalog_roots()`
rather than copied from it, so the ids callers may send cannot drift from the ids the service
can serve. Every surface — `POST /v1/code/ask`, `GET /ask`, `GET /v1/code/symbols`,
`GET /v1/catalog`, `reindex`, and the CLI — goes through it.

An id is not a slug: `production_rag` is legal and the underscore in it means nothing. What the
shape forbids is everything a path needs — separators, dots, drive colons, NUL. That is a
defense-in-depth check, not the boundary; the boundary is membership in the catalog. A caller
reaching for the filesystem gets `400` and a typo gets `404`, and neither answer reveals what
the catalog holds.

The environment may replace the *root* behind an existing id (`REPOMIND_CATALOG_PRODUCTION_RAG`)
for local dogfooding. It cannot add an id, and evals ignore it entirely, so CI always measures
committed bytes.

### The tree gets a hash

Every visible file carries a blob hash and every repository a `tree_hash` folded from the sorted
`(path, blob_hash)` pairs. Path is inside the hash, so moving a file changes the tree even when
no byte of content does. Walk order is not, so an implementation detail of `os.walk` cannot
change a published address.

Python files are hashed after decoding and CRLF normalization. Without that, one commit checked
out on Windows and on Linux would advertise two different indexes for identical history.

`INDEXER_VERSION` is folded in as well, and is part of every cache key. The same bytes read by
different chunking rules are not the same index, and an ingestor built by an older indexer must
never hand back chunks an upgraded one would not produce.

Each chunk also carries its own `content_hash` over `(kind, qualname, text)` — what the
definition *is*, deliberately not where it sits, so a definition that moves down its file keeps
its address while an edited body loses it.

`GET /v1/catalog` publishes `repo_id`, file count, indexed file count, chunk count, tree hash,
and indexer version. Two instances reporting the same tree hash and indexer version are
answering from the same index; either one differing explains why they differ.

### Re-ingest of unchanged bytes does no work

`IncrementalIngestor` caches chunks per repository-relative path, validated by blob hash. A
second ingest of an unchanged tree parses zero files, and an edit costs one parse rather than a
repository. Reuse is decided by content, so touching a file without changing it is still a
no-op and a stale entry cannot survive an edit. This is asserted, not asserted-about: see
`tests/test_incremental.py`.

## Why the hosted instance cannot take a stranger's zip

The obvious next feature is an upload box, and it is not being built. Accepting arbitrary
archives would mean:

- **Executing the untrusted decision of what to read.** The walker already refuses symlinks and
  honors nested `.gitignore`, but an attacker-authored archive is an adversary against those
  rules (path traversal in entry names, symlink entries, zip bombs), not a user of them.
- **Serving content on somebody else's behalf.** A public endpoint that indexes and echoes
  uploaded source becomes a way to launder and redistribute code through this domain.
- **Unbounded per-request work on a shared function.** Ingest cost would become caller-chosen.
- **Losing the honesty of the score.** 14/14 and 8/8 are regression gates over *committed*
  bytes. If the corpus were caller-supplied, the numbers on the README would describe nothing.

The hosted instance indexes only fixtures committed to this repository. That is a smaller claim
than "we index GitHub", and it is one every reader can verify by reading the repository.

Local operators who want another root have the environment override, which is the same closed
catalog with one root repointed — not a new door.

## Consequences

- The index has an identity that survives redeployment and can be compared across instances.
- Re-ingest is proportional to the change; the fixtures are small, so the win is the
  *guarantee*, not the milliseconds.
- Bumping `INDEXER_VERSION` invalidates every cache and changes every published tree hash. That
  is the intended cost of changing what a chunk means.
- There is still no persistence: the cache lives in the process. A cold start pays a full
  ingest. Adding a durable store is possible precisely because the addresses now exist, but it
  is not part of this decision.

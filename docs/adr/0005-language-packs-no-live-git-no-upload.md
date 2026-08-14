# ADR 0005 — Language packs, no live git on host, no zip upload

**Status:** Accepted  
**Date:** 2026-08-14

## Context

v0.3.0 indexes Python (stdlib `ast`) and a free-path JS scanner, with optional
tree-sitter behind an extra that default CI never installs. The v1 season needs
a third language surface without turning CI into a grammar download network
hop, and without opening the hosted catalog to stranger paths or archives.

## Decision

1. **Language packs** are a small in-repo registry (`repomind.ingest.packs`):
   each pack declares suffixes, a pure chunk function, and an honesty label.
   Defaults: `python-ast`, `js`, `json` (stdlib `json` top-level keys).
2. **Default CI never downloads grammars.** tree-sitter remains an optional
   extra with `pytest.importorskip` / marker skip.
3. **History on the host stays snapshot-first** (ADR 0004). Rename awareness is a
   committed `.repomind/renames.jsonl` map, not `git log` on Vercel.
4. **No zip/path upload.** The catalog allowlist is the only way to name a
   repository. Offline `repomind pack` / `unpack` is a lab artifact; production
   continues to ship fixtures via `includeFiles`.

## Consequences

- INDEXER_VERSION bumps when pack rules change (v3 for packs + JSON).
- Goldens can target JSON fields and rename questions without network.
- Operators cannot point the host at arbitrary disks; honesty stays high.

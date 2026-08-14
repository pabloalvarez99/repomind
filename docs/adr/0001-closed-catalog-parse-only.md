# ADR 0001: Closed catalog and parse-only ingestion

Status: accepted for v0.1.0.

RepoMind accepts a repository id, never a caller filesystem path. The server owns the closed
mapping and reads selected Python files as text for `ast.parse`; it does not import them.
Symlinks, cache directories, and hierarchical gitignored paths are skipped.

This limits the demo surface and prevents path traversal or repository code execution. The
trade-off is intentional: v0.1.0 cannot index arbitrary user repositories through HTTP.

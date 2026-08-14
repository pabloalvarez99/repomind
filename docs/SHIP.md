# SHIP checklist — v0.1.0

## Product

- [x] One-sentence value prop for hiring managers.
- [x] Free demo path documented first.
- [x] Paid path separated: none exists or is required.
- [x] LIVE / DECLARED / PLANNED table in README.

## Engineering

- [x] `src/` package, `pyproject.toml`, Python 3.12+.
- [x] Offline unit and HTTP integration tests.
- [x] Ruff and strict mypy.
- [x] CI on push and pull request with empty provider keys.
- [x] ADRs for the catalog/sandbox and lexical baseline.
- [x] JSON HTTP completion logs with request correlation id.

## Trust

- [x] No credentials required or committed.
- [x] `SECURITY.md` and `CONTRIBUTING.md`.
- [x] MIT license.
- [x] Eval metrics disclose deterministic provider, null judge, and $0 bill.

## Polish

- [x] CI, Python, and license badges.
- [x] Architecture diagram.
- [x] Free-path console covered by live HTTP tests.

## Release evidence

- Mini eval: 14/14 committed cases.
- Production RAG dogfood: 8/8 committed snapshot cases.
- CLI stdout: exactly one JSON object.
- UI: local assets, labeled controls, citation/refusal states, request id.
- Container: Python 3.12 slim, unprivileged runtime, port 8020.

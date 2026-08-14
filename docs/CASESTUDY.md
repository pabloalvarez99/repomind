# Case study: honest code evidence without a model

## Problem

Code assistants often make two trust-eroding moves: accept an overly broad filesystem target
and answer without a precise source location. RepoMind explores a narrower hiring-grade
baseline: can a service locate useful Python definitions, cite exact lines, and refuse when it
has no evidence—fully offline and for $0?

## Why AST chunks

Fixed-size text windows blur definition boundaries and make line evidence unstable. Python's
AST already provides semantic units and `lineno`/`end_lineno`. RepoMind emits a chunk for each
class, function, async function, and method. The contract is intentionally inspectable:
`chunk_id = path::qualname`, with path, kind, line range, and source text in the payload.

## Sandbox choice

Repository ids select a closed server-owned catalog. RepoMind reads source as text, skips
symlinks and ignored/cache paths, and never imports the target. This is not a complete hostile
repository sandbox, but it removes code execution and caller-selected filesystem traversal
from the v0.1.0 path.

## Dogfood without inflated claims

The `production_rag` catalog is a small frozen selection from a real sibling project at
approximately `d882c9a`. Eight committed questions locate its query entry, graph builder,
reciprocal-rank fusion, fake provider, guardrail, and API route, plus prose and refusal cases.
The existing mini suite remains the 14-case regression gate.

Both scorecards report `provider: deterministic-lexical`, `judge: null`, and
`billed_usd: 0.0`. A perfect result demonstrates stable navigation and citations on those
bytes. It does not demonstrate semantic understanding, arbitrary-repository generalization,
or code-RAG SOTA.

## Result

v0.1.0 provides one implementation across CLI, JSON API, symbol outline, and accessible local
UI. Exact symbol requests return only exact definitions; weak evidence returns the fixed
refusal with no citations. CI installs from scratch on Python 3.12 with empty provider keys and
runs lint, strict types, tests, both evals, CLI, and live HTTP/UI probes.

# Code-question evaluation set

`code_questions.jsonl` is RepoMind's committed, deterministic regression gate. It contains
14 fixture-backed questions: 10 answerable retrieval cases and four cases that must refuse.

## Record schema

Each line is one JSON object:

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable, unique case identifier. |
| `question` | yes | Natural-language question sent to the code Q&A service. |
| `expected_path` | answerable cases | Repository-relative path that must appear in a citation. |
| `expected_symbol` | answerable cases | Symbol text that must appear in the answer. |
| `expect_refusal` | refusal cases | When `true`, the response must contain no citations. |

Answerable cases cover exact-symbol lookup, prose phrasing, classes, methods, constructors,
and line-backed citations. Refusal cases cover unrelated questions plus definitions that are
gitignored or generated and therefore must not enter the index.

## Run it

From an editable development install:

```bash
python -m repomind.evals.run
```

The command exits non-zero if any case fails and prints one JSON summary with `total`,
`passed`, `failed`, `pass_rate`, and `failed_ids`. The provider is
`deterministic-lexical`; there is no model judge or billable call (`judge: null`,
`billed_usd: 0.0`).

## Interpretation

This set is a small regression test for the committed `mini` fixture. A perfect score does
not establish retrieval quality, language coverage, or generalization to arbitrary
repositories. Add cases when behavior changes; do not weaken an expectation merely to make
the gate pass.

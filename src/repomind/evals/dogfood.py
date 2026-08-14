"""Run the frozen Production RAG navigation and citation gate."""

from __future__ import annotations

import json

from repomind.catalog import PRODUCTION_RAG_REPO_ID
from repomind.evals.run import default_dataset_path, evaluate

DOGFOOD_DATASET = "dogfood_questions.jsonl"


def main() -> int:
    """Print the zero-cost dogfood scorecard as one JSON object."""
    summary = evaluate(
        default_dataset_path().with_name(DOGFOOD_DATASET),
        repo_id=PRODUCTION_RAG_REPO_ID,
    )
    print(json.dumps(summary, ensure_ascii=True, separators=(",", ":")))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

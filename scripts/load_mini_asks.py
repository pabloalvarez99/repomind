"""Run N local asks against the mini fixture and write p50/p95 JSON.

Honesty caption: lexical fixture, not GitHub-scale capacity planning.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from repomind.answer import CodeAskService
from repomind.catalog import MINI_REPO_ID, catalog_roots

QUESTIONS = (
    "Where is create_app defined?",
    "Where is health defined?",
    "Where is GreetingService defined?",
    "Where is greet defined?",
    "Where is boot defined?",
    "Who won the Antarctic chess championship?",
    "Where did create_app go after the rename?",
    "Where is service_name defined?",
)


def percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted list."""
    if not sorted_values:
        return 0.0
    rank = max(1, int(round(pct / 100.0 * len(sorted_values))))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def main() -> int:
    """Execute the load loop and write docs/assets/load.json by default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/assets/load.json"),
    )
    args = parser.parse_args()
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))
    durations_ms: list[float] = []
    answered = 0
    refused = 0
    for index in range(args.n):
        question = QUESTIONS[index % len(QUESTIONS)]
        started = time.perf_counter()
        response = service.ask(question, repo_id=MINI_REPO_ID)
        durations_ms.append((time.perf_counter() - started) * 1000.0)
        if response.citations:
            answered += 1
        else:
            refused += 1
    ordered = sorted(durations_ms)
    payload = {
        "n": args.n,
        "repo_id": MINI_REPO_ID,
        "answered": answered,
        "refused": refused,
        "p50_ms": round(percentile(ordered, 50), 3),
        "p95_ms": round(percentile(ordered, 95), 3),
        "mean_ms": round(statistics.fmean(durations_ms), 3) if durations_ms else 0.0,
        "billed_usd": 0.0,
        "provider": "deterministic-lexical",
        "honesty": "lexical fixture, not GitHub-scale",
        "hardware_note": "single local process; not capacity planning",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

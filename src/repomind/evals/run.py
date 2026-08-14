"""Run the committed code-question evaluation without a network or judge."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from repomind.answer import CodeAskService
from repomind.main import fixture_root

DEFAULT_DATASET: Final = "code_questions.jsonl"


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One expected retrieval or refusal behavior."""

    case_id: str
    question: str
    expected_path: str | None
    expected_symbol: str | None
    expect_refusal: bool

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> EvaluationCase:
        """Validate the small JSONL contract without a second model stack."""
        return cls(
            case_id=str(payload["id"]),
            question=str(payload["question"]),
            expected_path=(
                str(payload["expected_path"]) if payload.get("expected_path") is not None else None
            ),
            expected_symbol=(
                str(payload["expected_symbol"])
                if payload.get("expected_symbol") is not None
                else None
            ),
            expect_refusal=bool(payload.get("expect_refusal", False)),
        )


def default_dataset_path() -> Path:
    """Return the packaged dataset, with an editable-install fallback."""
    packaged = Path(str(files("repomind").joinpath("data", "eval", DEFAULT_DATASET)))
    if packaged.is_file():
        return packaged
    return Path(__file__).resolve().parents[3] / "data" / "eval" / DEFAULT_DATASET


def load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    """Load non-empty JSONL records in source order."""
    cases: list[EvaluationCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"evaluation line {line_number} is not an object")
        cases.append(EvaluationCase.from_payload(payload))
    if not cases:
        raise ValueError("evaluation dataset is empty")
    return tuple(cases)


def evaluate(path: Path | None = None) -> dict[str, Any]:
    """Evaluate exact fixture retrieval and refusal expectations."""
    cases = load_cases(default_dataset_path() if path is None else path)
    service = CodeAskService.from_roots({"mini": fixture_root()})
    failures: list[str] = []

    for case in cases:
        response = service.ask(case.question)
        refused = not response.citations
        passed = refused == case.expect_refusal
        if case.expected_path is not None:
            passed = passed and any(
                citation.path == case.expected_path for citation in response.citations
            )
        if case.expected_symbol is not None:
            passed = passed and case.expected_symbol in response.answer
        if not passed:
            failures.append(case.case_id)

    passed_count = len(cases) - len(failures)
    return {
        "total": len(cases),
        "passed": passed_count,
        "failed": len(failures),
        "pass_rate": passed_count / len(cases),
        "failed_ids": failures,
        "provider": "deterministic-lexical",
        "judge": None,
        "billed_usd": 0.0,
    }


def main() -> int:
    """Run the dataset named on the command line and print one JSON summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=None)
    namespace = parser.parse_args()
    summary = evaluate(namespace.dataset)
    print(json.dumps(summary, ensure_ascii=True, separators=(",", ":")))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

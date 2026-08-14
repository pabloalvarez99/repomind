"""Run the free-path program set (n≥50 target) with multi-repo rows."""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from repomind.answer import CodeAskService
from repomind.catalog import MINI_REPO_ID, catalog_roots
from repomind.evals.difficulty import ProgramCase, check_program_difficulty

PROGRAM_DATASET: Final = "program_questions.jsonl"


def default_program_path() -> Path:
    """Return the packaged program dataset, with editable-install fallback."""
    packaged = Path(str(files("repomind").joinpath("data", "eval", PROGRAM_DATASET)))
    if packaged.is_file():
        return packaged
    return Path(__file__).resolve().parents[3] / "data" / "eval" / PROGRAM_DATASET


def load_program_cases(path: Path | None = None) -> tuple[ProgramCase, ...]:
    """Load program JSONL rows in source order."""
    target = default_program_path() if path is None else path
    cases: list[ProgramCase] = []
    for line_number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"program line {line_number} is not an object")
        cases.append(ProgramCase.from_payload(payload, default_repo=MINI_REPO_ID))
    if not cases:
        raise ValueError("program dataset is empty")
    return tuple(cases)


def evaluate_program(path: Path | None = None) -> dict[str, Any]:
    """Score program cases and attach difficulty integrity results."""
    cases = load_program_cases(path)
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))
    failures: list[str] = []
    for case in cases:
        response = service.ask(case.question, repo_id=case.repo_id)
        refused = not response.citations
        passed = refused == case.expect_refusal
        if case.expected_path is not None:
            passed = passed and any(
                citation.path == case.expected_path for citation in response.citations
            )
        if case.expected_symbol is not None and not case.expect_refusal:
            passed = passed and case.expected_symbol in response.answer
        if not passed:
            failures.append(case.case_id)

    difficulty_failures = check_program_difficulty(cases, service=service)
    source_sha = None
    for entry in service.catalog():
        if entry.repo_id == "production_rag":
            source_sha = entry.source_sha
            break

    passed_count = len(cases) - len(failures)
    return {
        "total": len(cases),
        "passed": passed_count,
        "failed": len(failures),
        "pass_rate": passed_count / len(cases),
        "failed_ids": failures,
        "difficulty_failures": difficulty_failures,
        "difficulty_ok": not difficulty_failures,
        "slices": sorted({case.slice for case in cases}),
        "production_rag_source_sha": source_sha,
        "provider": "deterministic-lexical",
        "judge": None,
        "billed_usd": 0.0,
    }


def main() -> int:
    """Print one JSON summary; exit 1 on case or difficulty failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=None)
    namespace = parser.parse_args()
    summary = evaluate_program(namespace.dataset)
    print(json.dumps(summary, ensure_ascii=True, separators=(",", ":")))
    if summary["failed"] or not summary["difficulty_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

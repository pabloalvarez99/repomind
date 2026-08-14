"""Mechanical difficulty predicates for the free-path program set.

A slice that is *all* exact-symbol rank-1 trivial locate questions fails unless
it is the capped ``symbol-easy`` slice. Labels alone never pass integrity.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from repomind.answer import CodeAskService
from repomind.catalog import catalog_roots
from repomind.index.memory import identifiers
from repomind.ingest.renames import load_renames

# Slices that must not collapse to exact-symbol rank-1 triviality.
RANK_STRESS_SLICES: Final = frozenset(
    {"cross-file", "rename/history", "dogfood-locate", "js-symbol", "json-field"}
)
SYMBOL_EASY_SLICE: Final = "symbol-easy"
SYMBOL_EASY_MAX_SHARE: Final = 0.30


@dataclass(frozen=True, slots=True)
class ProgramCase:
    """One program evaluation row with a difficulty slice."""

    case_id: str
    question: str
    repo_id: str
    slice: str
    expected_path: str | None
    expected_symbol: str | None
    expect_refusal: bool
    mention_path: str | None = None
    old_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any], *, default_repo: str) -> ProgramCase:
        """Parse one JSONL object into a typed program case."""
        return cls(
            case_id=str(payload["id"]),
            question=str(payload["question"]),
            repo_id=str(payload.get("repo_id") or default_repo),
            slice=str(payload.get("slice") or SYMBOL_EASY_SLICE),
            expected_path=(
                str(payload["expected_path"]) if payload.get("expected_path") is not None else None
            ),
            expected_symbol=(
                str(payload["expected_symbol"])
                if payload.get("expected_symbol") is not None
                else None
            ),
            expect_refusal=bool(payload.get("expect_refusal", False)),
            mention_path=(
                str(payload["mention_path"]) if payload.get("mention_path") is not None else None
            ),
            old_path=str(payload["old_path"]) if payload.get("old_path") is not None else None,
        )


def is_exact_symbol_locate(question: str, expected_symbol: str | None) -> bool:
    """Return whether the question names the expected symbol as an identifier."""
    if not expected_symbol:
        return False
    return expected_symbol.casefold() in identifiers(question)


def expected_rank(
    service: CodeAskService,
    case: ProgramCase,
    *,
    limit: int = 10,
) -> int | None:
    """Return 1-based rank of the expected path/symbol, or None if missing."""
    if case.expect_refusal or case.expected_path is None:
        return None
    # Rename answers bypass lexical rank; treat as non-rank-1 stress success when map hits.
    if case.slice == "rename/history":
        return 2
    index = service._indexes[case.repo_id]  # noqa: SLF001 — eval integrity only
    results = index.search(case.question, limit=limit)
    for rank, result in enumerate(results, start=1):
        path_ok = result.chunk.path == case.expected_path
        symbol_ok = True
        if case.expected_symbol is not None:
            leaf = result.chunk.qualname.rsplit(".", maxsplit=1)[-1]
            symbol_ok = (
                case.expected_symbol.casefold() in result.chunk.qualname.casefold()
                or case.expected_symbol.casefold() == leaf.casefold()
            )
        if path_ok and symbol_ok:
            return rank
    return None


def check_program_difficulty(
    cases: Sequence[ProgramCase],
    *,
    service: CodeAskService | None = None,
) -> list[str]:
    """Return human-readable failures; empty list means predicates pass."""
    failures: list[str] = []
    if not cases:
        failures.append("program set is empty")
        return failures

    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        failures.append("duplicate case ids in program set")

    n = len(cases)
    counts = Counter(case.slice for case in cases)
    easy = counts.get(SYMBOL_EASY_SLICE, 0)
    easy_cap = max(1, math.ceil(SYMBOL_EASY_MAX_SHARE * n))
    if easy > easy_cap:
        failures.append(
            f"{SYMBOL_EASY_SLICE} has {easy} items but cap is {easy_cap} (30% of n={n})"
        )

    for case in cases:
        if case.slice == "cross-file":
            if case.expect_refusal:
                failures.append(f"{case.case_id}: cross-file cannot be refusal")
                continue
            if not case.mention_path or not case.expected_path:
                failures.append(f"{case.case_id}: cross-file requires mention_path and expected_path")
            elif case.mention_path == case.expected_path:
                failures.append(f"{case.case_id}: cross-file mention_path equals expected_path")
        if case.slice == "unanswerable" and not case.expect_refusal:
            failures.append(f"{case.case_id}: unanswerable must expect_refusal")
        if case.slice == "js-symbol" and case.expected_path and not case.expected_path.endswith(
            (".js", ".ts", ".tsx", ".jsx")
        ):
            failures.append(f"{case.case_id}: js-symbol expected_path must be JS/TS")
        if case.slice == "json-field" and case.expected_path and not case.expected_path.endswith(
            ".json"
        ):
            failures.append(f"{case.case_id}: json-field expected_path must be .json")
        if case.slice == "rename/history":
            if case.expect_refusal:
                failures.append(f"{case.case_id}: rename/history cannot be refusal")
            if not case.old_path and "where did" not in case.question.casefold():
                failures.append(f"{case.case_id}: rename/history needs old_path or where-did prose")

    ask_service = service or CodeAskService.from_roots(catalog_roots(allow_environment=False))
    roots = getattr(ask_service, "_roots", {})
    for case in cases:
        if case.slice == "rename/history" and case.old_path:
            records = load_renames(roots[case.repo_id]) if case.repo_id in roots else ()
            if not any(record.old_path == case.old_path for record in records):
                failures.append(
                    f"{case.case_id}: old_path {case.old_path!r} missing from renames.jsonl"
                )

    # Rank-1 collapse: for stress slices, fail if every answerable item is an
    # exact-symbol locate that already ranks first.
    by_slice: dict[str, list[ProgramCase]] = {}
    for case in cases:
        by_slice.setdefault(case.slice, []).append(case)

    for slice_name, slice_cases in by_slice.items():
        if slice_name not in RANK_STRESS_SLICES:
            continue
        answerable = [case for case in slice_cases if not case.expect_refusal]
        if not answerable:
            continue
        trivial = 0
        for case in answerable:
            rank = expected_rank(ask_service, case)
            if (
                rank == 1
                and is_exact_symbol_locate(case.question, case.expected_symbol)
                and case.slice != "rename/history"
            ):
                trivial += 1
        if trivial == len(answerable) and slice_name != "rename/history":
            failures.append(
                f"slice {slice_name!r} is all trivial exact-symbol rank-1 "
                f"({trivial}/{len(answerable)}); rewrite questions or labels"
            )
        # Soft bar: more than 80% exact rank-1 also fails for stress slices.
        if len(answerable) >= 3 and trivial / len(answerable) > 0.8 and slice_name != "rename/history":
            failures.append(
                f"slice {slice_name!r} is >80% trivial exact-symbol rank-1 "
                f"({trivial}/{len(answerable)})"
            )

    return failures

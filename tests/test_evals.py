"""Evaluation dataset and harness tests."""

from pathlib import Path

import pytest

from repomind.catalog import PRODUCTION_RAG_CATALOG_ENV, PRODUCTION_RAG_REPO_ID
from repomind.evals.dogfood import DOGFOOD_DATASET
from repomind.evals.run import default_dataset_path, evaluate, load_cases


def test_dataset_has_at_least_twelve_unique_questions() -> None:
    """The fixture gate is broad enough to catch ranking regressions."""
    cases = load_cases(default_dataset_path())

    assert len(cases) >= 12
    assert len({case.case_id for case in cases}) == len(cases)
    assert len({case.question for case in cases}) == len(cases)
    assert any(case.expect_refusal for case in cases)
    assert any(not case.expect_refusal for case in cases)


def test_committed_evaluation_is_green_and_unbilled() -> None:
    """All declared fixture expectations pass without a provider or judge."""
    summary = evaluate()

    assert summary["total"] >= 12
    assert summary["failed"] == 0
    assert summary["pass_rate"] == 1.0
    assert summary["provider"] == "deterministic-lexical"
    assert summary["judge"] is None
    assert summary["billed_usd"] == 0.0


def test_dogfood_dataset_has_eight_cases_and_passes() -> None:
    """The curated P1 snapshot stays navigable with exact path:line evidence."""
    path = default_dataset_path().with_name(DOGFOOD_DATASET)
    cases = load_cases(path)
    summary = evaluate(path, repo_id=PRODUCTION_RAG_REPO_ID)

    assert len(cases) >= 8
    assert any(case.expect_refusal for case in cases)
    assert summary["failed"] == 0
    assert summary["provider"] == "deterministic-lexical"
    assert summary["judge"] is None
    assert summary["billed_usd"] == 0.0


def test_dogfood_eval_ignores_local_catalog_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CI score cannot silently measure a developer's sibling checkout."""
    monkeypatch.setenv(PRODUCTION_RAG_CATALOG_ENV, str(tmp_path))
    path = default_dataset_path().with_name(DOGFOOD_DATASET)

    summary = evaluate(path, repo_id=PRODUCTION_RAG_REPO_ID)

    assert summary["failed"] == 0

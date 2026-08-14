"""Evaluation dataset and harness tests."""

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

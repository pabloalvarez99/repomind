"""Program set size, slices, and difficulty predicates."""

from __future__ import annotations

import json
from pathlib import Path

from repomind.catalog import PRODUCTION_RAG_REPO_ID, catalog_roots
from repomind.evals.difficulty import check_program_difficulty
from repomind.evals.program import default_program_path, evaluate_program, load_program_cases
from repomind.ingest import IncrementalIngestor


def test_program_set_meets_n_and_passes_with_difficulty() -> None:
    """Season free-path program is large enough and integrity-green."""
    cases = load_program_cases()
    summary = evaluate_program()

    assert len(cases) >= 50
    assert summary["failed"] == 0
    assert summary["difficulty_ok"] is True
    assert summary["billed_usd"] == 0.0
    assert summary["judge"] is None
    assert "symbol-easy" in summary["slices"]
    assert "cross-file" in summary["slices"]
    assert "rename/history" in summary["slices"]
    assert "unanswerable" in summary["slices"]


def test_difficulty_rejects_all_easy_stress_slice(tmp_path: Path) -> None:
    """A stress slice made of exact-symbol rank-1 locates must fail integrity."""
    rows = [
        {
            "id": "a",
            "question": "Where is create_app defined?",
            "repo_id": "mini",
            "slice": "cross-file",
            "expected_path": "app/main.py",
            "expected_symbol": "create_app",
            "mention_path": "app/service.py",
        },
        {
            "id": "b",
            "question": "Where is health defined?",
            "repo_id": "mini",
            "slice": "cross-file",
            "expected_path": "app/main.py",
            "expected_symbol": "health",
            "mention_path": "app/service.py",
        },
        {
            "id": "c",
            "question": "Where is boot defined?",
            "repo_id": "mini",
            "slice": "cross-file",
            "expected_path": "app/main.py",
            "expected_symbol": "boot",
            "mention_path": "app/service.py",
        },
    ]
    path = tmp_path / "bad.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    cases = load_program_cases(path)
    failures = check_program_difficulty(cases)
    assert failures
    assert any("trivial" in item or "rank-1" in item for item in failures)


def test_production_rag_pin_is_current_and_noop_on_second_ingest() -> None:
    """Dogfood pin records bf6e36d-or-newer and re-ingest is a no-op."""
    roots = catalog_roots(allow_environment=False)
    root = roots[PRODUCTION_RAG_REPO_ID]
    pin = root / ".repomind" / "source.json"
    text = pin.read_text(encoding="utf-8")
    assert "bf6e36d" in text or "bf6e36d1d4ca353c4f17f649cb721da51d74f6bb" in text

    ingestor = IncrementalIngestor(root)
    first = ingestor.ingest()
    second = ingestor.ingest()
    assert first.stats.parsed_files > 0
    assert second.stats.is_noop
    assert second.snapshot.tree_hash == first.snapshot.tree_hash


def test_program_dataset_is_packaged() -> None:
    """Editable/packaged installs can still find the program set."""
    assert default_program_path().is_file()

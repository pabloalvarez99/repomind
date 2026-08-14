"""Command-line contract tests."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from repomind.cli import EXIT_ANSWERED, EXIT_BAD_REPO_ID, EXIT_REFUSED, main


def test_cli_answer_is_exactly_one_json_line() -> None:
    """The documented command is safe for a machine-readable pipeline."""
    stdout = io.StringIO()

    code = main(["ask", "Where is create_app defined?", "--fixture", "mini"], stdout=stdout)

    lines = stdout.getvalue().splitlines()
    payload = json.loads(lines[0])
    assert code == EXIT_ANSWERED
    assert len(lines) == 1
    assert payload["citations"][0]["path"] == "app/main.py"
    assert payload["citations"][0]["start_line"] == 6


def test_cli_refusal_is_json_and_nonzero() -> None:
    """A refusal stays parseable and signals no answer to shell callers."""
    stdout = io.StringIO()

    code = main(["ask", "Where is the lunar payroll database?"], stdout=stdout)

    assert code == EXIT_REFUSED
    assert json.loads(stdout.getvalue())["citations"] == []


def test_cli_can_query_the_production_rag_catalog() -> None:
    """Both documented selector names resolve the frozen dogfood snapshot."""
    for option in ("--repo", "--fixture"):
        stdout = io.StringIO()

        code = main(
            ["ask", "Where is run_query defined?", option, "production_rag"],
            stdout=stdout,
        )

        lines = stdout.getvalue().splitlines()
        assert code == EXIT_ANSWERED
        assert len(lines) == 1
        assert lines[0].startswith("{")
        assert json.loads(lines[0])["citations"][0]["path"] == (
            "production_rag/query_pipeline.py"
        )
        assert len(json.loads(lines[0])["citations"]) == 1


@pytest.mark.parametrize("repo_id", ["unknown", "../../etc", "   "])
def test_cli_rejects_a_bad_repository_id_without_touching_the_filesystem(repo_id: str) -> None:
    """The CLI shares the HTTP validity function instead of an argparse allowlist."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = main(["ask", "Where is create_app?", "--repo", repo_id], stdout=stdout, stderr=stderr)

    assert code == EXIT_BAD_REPO_ID
    assert stdout.getvalue() == ""
    assert "Known ids: mini, production_rag, mini_js" in stderr.getvalue()


def test_python_module_command_works_outside_the_checkout(tmp_path: Path) -> None:
    """The installed module finds its packaged fixture from another directory."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "repomind",
            "ask",
            "Where is create_app defined?",
            "--fixture",
            "mini",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == EXIT_ANSWERED
    assert len(completed.stdout.splitlines()) == 1
    assert json.loads(completed.stdout)["citations"][0]["path"] == "app/main.py"

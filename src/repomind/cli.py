"""Command-line interface for deterministic repository questions."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import IO, Final

from repomind.answer import CodeAskService
from repomind.main import fixture_root

EXIT_ANSWERED: Final = 0
EXIT_REFUSED: Final = 1


def build_parser() -> argparse.ArgumentParser:
    """Build the ``repomind`` command parser."""
    parser = argparse.ArgumentParser(
        prog="repomind",
        description="Ask deterministic questions about an indexed code fixture.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="Answer from AST-indexed code evidence.")
    ask.add_argument("question", help="Question or symbol to locate.")
    ask.add_argument(
        "--fixture",
        choices=("mini",),
        default="mini",
        help="Committed fixture repository to index (default: mini).",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: IO[str] | None = None) -> int:
    """Run one CLI command and emit exactly one JSON line on success or refusal."""
    namespace = build_parser().parse_args(argv)
    output = sys.stdout if stdout is None else stdout
    service = CodeAskService.from_roots({"mini": fixture_root()})
    response = service.ask(namespace.question, repo_id=namespace.fixture)
    output.write(
        json.dumps(response.model_dump(mode="json"), ensure_ascii=True, separators=(",", ":"))
        + "\n"
    )
    output.flush()
    return EXIT_ANSWERED if response.citations else EXIT_REFUSED

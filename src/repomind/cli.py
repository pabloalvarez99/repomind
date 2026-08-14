"""Command-line interface for deterministic repository questions."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Final

from repomind.answer import CodeAskService
from repomind.catalog import (
    MINI_REPO_ID,
    BlankRepositoryId,
    MalformedRepositoryId,
    UnknownRepository,
    catalog_ids,
    catalog_roots,
)
from repomind.packaging import pack_catalog, unpack_catalog

EXIT_ANSWERED: Final = 0
EXIT_REFUSED: Final = 1
EXIT_BAD_REPO_ID: Final = 2
EXIT_ERROR: Final = 3


def build_parser() -> argparse.ArgumentParser:
    """Build the ``repomind`` command parser."""
    parser = argparse.ArgumentParser(
        prog="repomind",
        description="Ask deterministic questions about an indexed code fixture.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="Answer from AST-indexed code evidence.")
    ask.add_argument("question", help="Question or symbol to locate.")
    # Deliberately no argparse ``choices``: that would be a second allowlist to keep
    # in step with the catalog. The id goes through repomind.catalog.validate_repo_id
    # like every other surface, and the help text names the ids the catalog serves.
    ask.add_argument(
        "--repo",
        "--fixture",
        dest="repo_id",
        default=MINI_REPO_ID,
        help=f"Catalog repository to index: {', '.join(catalog_ids())} (default: {MINI_REPO_ID}).",
    )
    pack = commands.add_parser(
        "pack",
        help="Write an offline fixtures+index pack (directory or .tar.gz).",
    )
    pack.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Destination directory or .tar.gz path.",
    )
    pack.add_argument(
        "--tarball",
        action="store_true",
        help="Emit a gzipped tarball instead of a directory.",
    )
    unpack = commands.add_parser(
        "unpack",
        help="Load an offline pack into a destination directory.",
    )
    unpack.add_argument("source", type=Path, help="Pack directory or .tar.gz.")
    unpack.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Directory to materialize the pack into.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
) -> int:
    """Run one CLI command and emit exactly one JSON line on success or refusal."""
    namespace = build_parser().parse_args(argv)
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr

    if namespace.command == "pack":
        as_tarball = bool(namespace.tarball) or str(namespace.out).endswith(".tar.gz")
        path = pack_catalog(namespace.out, as_tarball=as_tarball)
        output.write(
            json.dumps(
                {"path": str(path), "billed_usd": 0.0, "command": "pack"},
                ensure_ascii=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        output.flush()
        return EXIT_ANSWERED

    if namespace.command == "unpack":
        try:
            manifest = unpack_catalog(namespace.source, namespace.out)
        except (OSError, FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
            errors.write(f"repomind: unpack failed: {error}\n")
            errors.flush()
            return EXIT_ERROR
        output.write(
            json.dumps(
                {
                    "command": "unpack",
                    "billed_usd": manifest.billed_usd,
                    "repomind_version": manifest.repomind_version,
                    "repositories": [row.get("repo_id") for row in manifest.repositories],
                },
                ensure_ascii=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        output.flush()
        return EXIT_ANSWERED

    service = CodeAskService.from_roots(catalog_roots())
    try:
        response = service.ask(namespace.question, repo_id=namespace.repo_id)
    except (BlankRepositoryId, MalformedRepositoryId, UnknownRepository) as error:
        errors.write(
            f"repomind: {error.__class__.__name__}: {namespace.repo_id!r} is not a catalog "
            f"repository. Known ids: {', '.join(catalog_ids())}\n"
        )
        errors.flush()
        return EXIT_BAD_REPO_ID
    output.write(
        json.dumps(response.model_dump(mode="json"), ensure_ascii=True, separators=(",", ":"))
        + "\n"
    )
    output.flush()
    return EXIT_ANSWERED if response.citations else EXIT_REFUSED

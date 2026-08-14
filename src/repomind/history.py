"""Read-only git log/blame over a catalog fixture root.

This is an optional capability, not a product surface for browsing GitHub. The
tool never accepts a remote URL, never runs ``git fetch``, and never treats a
caller string as a filesystem root — only a catalog ``repo_id`` plus a
repository-relative path that has already been validated to stay under that
root.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from repomind.catalog import validate_repo_id

HistoryMode = Literal["log", "blame"]

MAX_HISTORY_LIMIT: Final = 50
DEFAULT_HISTORY_LIMIT: Final = 5
_GIT_TIMEOUT_SECONDS: Final = 5


class CapabilityMissing(Exception):
    """A requested optional capability is unavailable on this host."""

    def __init__(self, capability: str, reason: str) -> None:
        """Record which optional capability is missing and why."""
        super().__init__(f"{capability}: {reason}")
        self.capability = capability
        self.reason = reason


class UnsafeHistoryPath(ValueError):
    """The caller-supplied path is not a safe repository-relative location."""


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One git log line or blame attribution."""

    sha: str
    summary: str
    author: str | None = None
    committed_at: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class HistoryResult:
    """Read-only history for one path inside a catalog repository."""

    repo_id: str
    path: str
    mode: HistoryMode
    entries: tuple[HistoryEntry, ...]


def _resolve_git() -> str:
    """Return the git binary path or raise capability_missing."""
    found = shutil.which("git")
    if found is None:
        raise CapabilityMissing("git_history", "git_not_found")
    return found


def _safe_relative_path(value: str) -> str:
    """Return a POSIX-relative path that cannot escape a repository root."""
    if not value or not value.strip():
        raise UnsafeHistoryPath("path must not be blank")
    candidate = value.replace("\\", "/").strip()
    if candidate.startswith("/") or candidate.startswith("~"):
        raise UnsafeHistoryPath("path must be repository-relative")
    parts = [part for part in candidate.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise UnsafeHistoryPath("path must stay inside the catalog root")
    if any(":" in part for part in parts):
        # Drive-letter and URL schemes are never legal relative components.
        raise UnsafeHistoryPath("path must be repository-relative")
    return "/".join(parts)


def _run_git(git: str, root: Path, args: list[str]) -> str:
    """Run a fixed git subcommand inside ``root`` with no shell expansion."""
    try:
        completed = subprocess.run(
            [git, "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CapabilityMissing("git_history", "git_execution_failed") from error
    if completed.returncode != 0:
        stderr = (completed.stderr or "").casefold()
        if "not a git repository" in stderr:
            raise CapabilityMissing("git_history", "repository_not_git")
        raise CapabilityMissing("git_history", "git_command_failed")
    return completed.stdout


def _ensure_git_repository(git: str, root: Path) -> None:
    """Fail closed when the catalog root is not itself a git work tree root.

    Being *inside* some parent work tree is not enough: committed fixtures live
    under the product repository, and answering history against that outer tree
    would leak the product's own commits as if they belonged to the fixture.
    """
    try:
        inside = subprocess.run(
            [git, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
        toplevel = subprocess.run(
            [git, "-C", str(root), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CapabilityMissing("git_history", "git_execution_failed") from error
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise CapabilityMissing("git_history", "repository_not_git")
    if toplevel.returncode != 0:
        raise CapabilityMissing("git_history", "repository_not_git")
    try:
        if Path(toplevel.stdout.strip()).resolve() != root.resolve():
            raise CapabilityMissing("git_history", "repository_not_git")
    except OSError as error:
        raise CapabilityMissing("git_history", "repository_not_git") from error


class GitHistoryService:
    """Resolve catalog ids to roots and run read-only git history queries."""

    def __init__(self, roots: Mapping[str, Path]) -> None:
        """Bind to catalog roots that the catalog already resolved."""
        self._roots = dict(roots)

    def history(
        self,
        *,
        repo_id: str,
        path: str,
        mode: HistoryMode = "log",
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> HistoryResult:
        """Return log or blame for one path under a catalog repository.

        Raises:
            BlankRepositoryId / MalformedRepositoryId / UnknownRepository: bad id.
            UnsafeHistoryPath: path is blank, absolute, or tries to escape.
            CapabilityMissing: git missing, root not a git repo, or command fails.
            ValueError: ``mode`` or ``limit`` is out of contract.
        """
        if mode not in ("log", "blame"):
            raise ValueError("mode must be 'log' or 'blame'")
        if limit < 1 or limit > MAX_HISTORY_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_HISTORY_LIMIT}")

        validated_repo = validate_repo_id(repo_id, known=self._roots)
        relative = _safe_relative_path(path)
        root = self._roots[validated_repo].resolve()
        absolute = (root / relative).resolve()
        try:
            absolute.relative_to(root)
        except ValueError as error:
            raise UnsafeHistoryPath("path must stay inside the catalog root") from error
        if not absolute.is_file():
            raise UnsafeHistoryPath("path does not name a file in the catalog root")

        git = _resolve_git()
        _ensure_git_repository(git, root)

        if mode == "log":
            raw = _run_git(
                git,
                root,
                [
                    "log",
                    f"-n{limit}",
                    "--format=%H%x09%an%x09%aI%x09%s",
                    "--",
                    relative,
                ],
            )
            entries = _parse_log(raw)
        else:
            raw = _run_git(
                git,
                root,
                ["blame", "--line-porcelain", f"-L1,{limit}", "--", relative],
            )
            entries = _parse_blame(raw)

        return HistoryResult(
            repo_id=validated_repo,
            path=relative,
            mode=mode,
            entries=entries,
        )


def _parse_log(raw: str) -> tuple[HistoryEntry, ...]:
    """Parse the fixed ``git log`` format into entries."""
    entries: list[HistoryEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", maxsplit=3)
        if len(parts) != 4:
            continue
        sha, author, committed_at, summary = parts
        entries.append(
            HistoryEntry(sha=sha, author=author, committed_at=committed_at, summary=summary)
        )
    return tuple(entries)


def _parse_blame(raw: str) -> tuple[HistoryEntry, ...]:
    """Parse porcelain blame into one entry per source line returned."""
    entries: list[HistoryEntry] = []
    sha = ""
    author = None
    committed_at = None
    summary = ""
    line_no: int | None = None
    for line in raw.splitlines():
        if not line:
            continue
        if line.startswith("\t"):
            entries.append(
                HistoryEntry(
                    sha=sha,
                    author=author,
                    committed_at=committed_at,
                    summary=summary or line[1:].strip(),
                    line=line_no,
                )
            )
            continue
        if line[0] in "0123456789abcdef" and " " in line:
            # header: <sha> <orig> <final> [<num>]
            fields = line.split()
            sha = fields[0]
            if len(fields) >= 3 and fields[2].isdigit():
                line_no = int(fields[2])
            continue
        if line.startswith("author "):
            author = line[len("author ") :]
        elif line.startswith("author-time "):
            committed_at = line[len("author-time ") :]
        elif line.startswith("summary "):
            summary = line[len("summary ") :]
    return tuple(entries)

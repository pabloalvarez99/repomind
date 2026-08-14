"""Safe, gitignore-aware repository discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pathspec import GitIgnoreSpec

ALWAYS_IGNORED: Final = (
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
)


@dataclass(frozen=True, slots=True)
class RepositoryFile:
    """A regular file proven to live beneath a repository root."""

    path: str
    absolute_path: Path


def _load_ignore_spec(root: Path) -> GitIgnoreSpec:
    """Compile root gitignore rules plus directories RepoMind must never index."""
    patterns = list(ALWAYS_IGNORED)
    ignore_file = root / ".gitignore"
    if ignore_file.is_file():
        patterns.extend(ignore_file.read_text(encoding="utf-8").splitlines())
    return GitIgnoreSpec.from_lines(patterns)


def walk_repository(root: Path) -> tuple[RepositoryFile, ...]:
    """Return sorted, non-symlink files allowed by the root ``.gitignore``.

    Args:
        root: Directory to inspect. It is resolved before walking.

    Returns:
        Files with POSIX relative paths, in deterministic lexical order.

    Raises:
        ValueError: ``root`` is not a directory.
    """
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")

    ignore = _load_ignore_spec(resolved_root)
    discovered: list[RepositoryFile] = []

    for directory, names, filenames in os.walk(resolved_root, followlinks=False):
        current = Path(directory)
        names[:] = sorted(
            name
            for name in names
            if not (current / name).is_symlink()
            and not ignore.match_file(
                (current / name).relative_to(resolved_root).as_posix() + "/"
            )
        )
        for filename in sorted(filenames):
            absolute = current / filename
            relative = absolute.relative_to(resolved_root).as_posix()
            if absolute.is_symlink() or ignore.match_file(relative):
                continue
            discovered.append(RepositoryFile(path=relative, absolute_path=absolute))

    return tuple(sorted(discovered, key=lambda item: item.path))

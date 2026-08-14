"""Safe, gitignore-aware repository discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pathspec import GitIgnoreSpec

ALWAYS_IGNORED: Final = (
    ".git/",
    ".repomind/",
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


@dataclass(frozen=True, slots=True)
class _IgnoreScope:
    """Gitignore rules interpreted relative to the directory that owns them."""

    directory: Path
    spec: GitIgnoreSpec


def _load_ignore_spec(directory: Path) -> GitIgnoreSpec | None:
    """Compile the gitignore owned by ``directory``, when present."""
    ignore_file = directory / ".gitignore"
    if ignore_file.is_file():
        return GitIgnoreSpec.from_lines(ignore_file.read_text(encoding="utf-8").splitlines())
    return None


def _is_ignored(path: Path, *, is_directory: bool, scopes: list[_IgnoreScope]) -> bool:
    """Apply ancestor scopes in order, letting the deepest matching rule win."""
    ignored = False
    for scope in scopes:
        try:
            relative = path.relative_to(scope.directory).as_posix()
        except ValueError:
            continue
        candidate = relative + "/" if is_directory else relative
        result = scope.spec.check_file(candidate)
        if result.include is not None:
            ignored = result.include
    return ignored


def _directory_is_visible(
    candidate: Path,
    *,
    root: Path,
    always_ignore: GitIgnoreSpec,
    scopes: list[_IgnoreScope],
) -> bool:
    """Return whether ``candidate`` is safe to descend into."""
    relative = candidate.relative_to(root).as_posix() + "/"
    return (
        not candidate.is_symlink()
        and not always_ignore.match_file(relative)
        and not _is_ignored(candidate, is_directory=True, scopes=scopes)
    )


def walk_repository(root: Path) -> tuple[RepositoryFile, ...]:
    """Return sorted, non-symlink files allowed by hierarchical gitignore rules.

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

    always_ignore = GitIgnoreSpec.from_lines(ALWAYS_IGNORED)
    scopes: list[_IgnoreScope] = []
    discovered: list[RepositoryFile] = []

    for directory, names, filenames in os.walk(resolved_root, followlinks=False):
        current = Path(directory)
        local_spec = _load_ignore_spec(current)
        if local_spec is not None:
            scopes.append(_IgnoreScope(directory=current, spec=local_spec))

        names[:] = sorted(
            name
            for name in names
            if _directory_is_visible(
                current / name,
                root=resolved_root,
                always_ignore=always_ignore,
                scopes=scopes,
            )
        )
        for filename in sorted(filenames):
            absolute = current / filename
            relative = absolute.relative_to(resolved_root).as_posix()
            if (
                absolute.is_symlink()
                or always_ignore.match_file(relative)
                or _is_ignored(absolute, is_directory=False, scopes=scopes)
            ):
                continue
            discovered.append(RepositoryFile(path=relative, absolute_path=absolute))

    return tuple(sorted(discovered, key=lambda item: item.path))

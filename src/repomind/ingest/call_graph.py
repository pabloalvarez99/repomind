"""Python AST incoming call references for catalog fixtures.

Fixture-only honesty: this module never clones a remote and never resolves
dynamic attributes. It walks Python sources under a catalog root, records every
plain ``Name`` or trailing ``Attribute`` call, and matches those names against
definitions already chunked from the same root.

A known symbol may have zero callers. That is a leaf, not a lie — empty lists
are returned as empty lists, never fabricated edges.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from repomind.ingest.chunk_python import CodeChunk, normalize_source
from repomind.ingest.walk import walk_repository

__all__ = ["CallSite", "build_incoming_refs", "incoming_for"]


@dataclass(frozen=True, slots=True)
class CallSite:
    """One call expression that names a catalog definition."""

    path: str
    line: int
    caller_qualname: str
    callee_name: str


class _CallVisitor(ast.NodeVisitor):
    """Collect call sites while tracking the enclosing definition stack."""

    def __init__(self, *, path: str) -> None:
        self._path = path
        self._stack: list[str] = []
        self.sites: list[CallSite] = []

    def _push(self, name: str) -> None:
        self._stack.append(name)

    def _pop(self) -> None:
        self._stack.pop()

    def _caller(self) -> str:
        return ".".join(self._stack) if self._stack else "<module>"

    def _callee_name(self, func: ast.expr) -> str | None:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast API
        """Record a call when the callee is a simple name or attribute."""
        name = self._callee_name(node.func)
        if name is not None:
            self.sites.append(
                CallSite(
                    path=self._path,
                    line=node.lineno,
                    caller_qualname=self._caller(),
                    callee_name=name,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Enter a class body so methods get a qualified caller name."""
        self._push(node.name)
        self.generic_visit(node)
        self._pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Enter a function or method body."""
        self._push(node.name)
        self.generic_visit(node)
        self._pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """Enter an async function or method body."""
        self._push(node.name)
        self.generic_visit(node)
        self._pop()


def _sites_for_source(*, path: str, source: str) -> tuple[CallSite, ...]:
    """Parse one file and return its call sites (empty on syntax error)."""
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return ()
    visitor = _CallVisitor(path=path)
    visitor.visit(tree)
    return tuple(visitor.sites)


def _matches(qualname: str, callee_name: str) -> bool:
    """Return whether a call name refers to this definition."""
    return qualname == callee_name or qualname.endswith("." + callee_name)


def build_incoming_refs(
    root: Path,
    *,
    definitions: Sequence[CodeChunk] | None = None,
) -> dict[str, tuple[CallSite, ...]]:
    """Return qualname → call sites for every definition under ``root``.

    Only Python files are considered. Non-Python catalog entries (e.g. mini_js)
    get an empty map. When ``definitions`` is omitted, only names that appear as
    call targets are keyed — prefer passing the index chunks so leaves with zero
    callers still appear with empty tuples.
    """
    sites: list[CallSite] = []
    for repository_file in walk_repository(root):
        if not repository_file.path.endswith(".py"):
            continue
        data = repository_file.absolute_path.read_bytes()
        source = normalize_source(data)
        sites.extend(_sites_for_source(path=repository_file.path, source=source))

    by_qualname: dict[str, list[CallSite]] = defaultdict(list)
    defined: Iterable[str]
    if definitions is not None:
        defined = (chunk.qualname for chunk in definitions if chunk.path.endswith(".py"))
        for qualname in defined:
            by_qualname.setdefault(qualname, [])
    else:
        defined = ()

    qualnames = list(by_qualname) if by_qualname else []
    if not qualnames and definitions is None:
        # No explicit definition list: key only by callee names seen.
        for site in sites:
            by_qualname[site.callee_name].append(site)
        return {
            name: tuple(
                sorted(group, key=lambda item: (item.path, item.line, item.caller_qualname))
            )
            for name, group in by_qualname.items()
        }

    if not qualnames and definitions is not None:
        for chunk in definitions:
            if chunk.path.endswith(".py"):
                by_qualname.setdefault(chunk.qualname, [])
        qualnames = list(by_qualname)

    for site in sites:
        for qualname in qualnames:
            if _matches(qualname, site.callee_name):
                by_qualname[qualname].append(site)

    return {
        name: tuple(
            sorted(group, key=lambda item: (item.path, item.line, item.caller_qualname))
        )
        for name, group in by_qualname.items()
    }


def incoming_for(
    refs: Mapping[str, tuple[CallSite, ...]],
    symbol: str,
) -> tuple[str, tuple[CallSite, ...]]:
    """Resolve a user symbol to a qualname and its incoming call sites.

    Prefers an exact qualname match, then a unique short-name match. When several
    qualnames share a short name, returns the lexicographically first with its
    sites (callers still honest; disambiguation is left to the UI).
    """
    if not symbol or not symbol.strip():
        return symbol, ()
    needle = symbol.strip()
    if needle in refs:
        return needle, refs[needle]
    short_hits = [
        (name, sites)
        for name, sites in sorted(refs.items())
        if name == needle or name.endswith("." + needle)
    ]
    if not short_hits:
        return needle, ()
    return short_hits[0]

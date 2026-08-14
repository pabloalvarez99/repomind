"""Committed rename maps for fixture history (no live git)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

RENAMES_RELATIVE_PATH: Final = Path(".repomind") / "renames.jsonl"


@dataclass(frozen=True, slots=True)
class RenameRecord:
    """One old_path → new_path mapping, optionally for a symbol."""

    old_path: str
    new_path: str
    symbol: str | None = None


def load_renames(root: Path) -> tuple[RenameRecord, ...]:
    """Load rename records from a catalog fixture root."""
    path = root / RENAMES_RELATIVE_PATH
    if not path.is_file():
        return ()
    records: list[RenameRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        old = row.get("old_path")
        new = row.get("new_path")
        if not isinstance(old, str) or not isinstance(new, str):
            continue
        symbol = row.get("symbol")
        records.append(
            RenameRecord(
                old_path=old.replace("\\", "/"),
                new_path=new.replace("\\", "/"),
                symbol=symbol if isinstance(symbol, str) and symbol.strip() else None,
            )
        )
    return tuple(records)


def find_rename(
    records: tuple[RenameRecord, ...],
    *,
    symbol: str | None = None,
    old_path: str | None = None,
) -> RenameRecord | None:
    """Return the first rename matching symbol and/or old_path."""
    for record in records:
        if old_path is not None and record.old_path != old_path.replace("\\", "/"):
            continue
        if symbol is not None and record.symbol is not None:
            if record.symbol.casefold() != symbol.casefold():
                continue
        elif symbol is not None and record.symbol is None:
            continue
        return record
    return None

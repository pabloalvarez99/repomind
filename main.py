"""Vercel zero-config FastAPI entry (repo root)."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from repomind.main import app  # noqa: E402  (import follows the sys.path bootstrap above)

__all__ = ["app"]

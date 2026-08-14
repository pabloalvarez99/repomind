"""Language packs, rename map, and offline pack round-trip."""

from __future__ import annotations

from pathlib import Path

from repomind.answer import CodeAskService
from repomind.catalog import MINI_REPO_ID, catalog_roots
from repomind.ingest import INDEXER_VERSION, JSON_SUFFIXES, PACKS, pack_for_suffix
from repomind.packaging import pack_catalog, unpack_catalog


def test_three_free_path_packs_registered_without_network() -> None:
    """python-ast, js, and json are default packs; no grammar download."""
    ids = {pack.pack_id for pack in PACKS}
    assert {"python-ast", "js", "json"} <= ids
    assert all(pack.default for pack in PACKS)
    assert pack_for_suffix(".json") is not None
    assert ".json" in JSON_SUFFIXES
    assert INDEXER_VERSION == "3"


def test_json_field_is_indexed_on_mini() -> None:
    """Structural JSON keys are answerable with path:line."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))
    answer = service.ask("Where is service_name defined?", repo_id=MINI_REPO_ID)
    assert answer.citations
    assert any(c.path == "config/settings.json" for c in answer.citations)
    assert "service_name" in answer.answer


def test_rename_question_cites_new_path() -> None:
    """Where did X go → new path:line from renames.jsonl + live index."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))
    answer = service.ask("Where did create_app go after the rename?", repo_id=MINI_REPO_ID)
    assert answer.citations
    assert answer.citations[0].path == "app/main.py"
    assert "application.py" in answer.answer or "moved" in answer.answer


def test_pack_unpack_round_trip(tmp_path: Path) -> None:
    """Offline pack carries manifest billed_usd 0 and repository meta."""
    out_dir = tmp_path / "pack"
    packed = pack_catalog(out_dir, as_tarball=False)
    assert (packed / "repomind-pack.json").is_file()
    dest = tmp_path / "unpacked"
    manifest = unpack_catalog(packed, dest)
    assert manifest.billed_usd == 0.0
    assert any(row.get("repo_id") == "mini" for row in manifest.repositories)
    assert any(row.get("repo_id") == "production_rag" for row in manifest.repositories)

"""Offline catalog pack / unpack (fixtures + index metadata, billed $0)."""

from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from repomind import __version__
from repomind.answer import CodeAskService
from repomind.catalog import catalog_roots
from repomind.ingest import INDEXER_VERSION

MANIFEST_NAME: Final = "repomind-pack.json"


@dataclass(frozen=True, slots=True)
class PackManifest:
    """Machine-readable description of one offline pack."""

    format_version: int
    repomind_version: str
    indexer_version: str
    created_at: str
    repositories: list[dict[str, Any]]
    billed_usd: float = 0.0


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def pack_catalog(
    destination: Path,
    *,
    roots: dict[str, Path] | None = None,
    as_tarball: bool = False,
) -> Path:
    """Write a directory (or ``.tar.gz``) of committed fixtures + catalog meta.

    Hosted deployments continue to use the in-repo fixtures; this pack is an
    offline lab artifact for round-trip and demos.
    """
    resolved_roots = catalog_roots(allow_environment=False) if roots is None else roots
    destination = destination.resolve()
    if as_tarball:
        work = destination.with_suffix("") if destination.suffixes else destination
        if work.suffix == ".tar":
            work = work.with_suffix("")
        work = Path(str(work) + "-dir")
    else:
        work = destination
    work.mkdir(parents=True, exist_ok=True)
    fixtures_out = work / "fixtures"
    fixtures_out.mkdir(exist_ok=True)

    service = CodeAskService.from_roots(resolved_roots)
    meta_by_id = {entry.repo_id: entry for entry in service.catalog()}
    repositories: list[dict[str, Any]] = []
    for repo_id, root in sorted(resolved_roots.items()):
        target = fixtures_out / repo_id
        _copy_tree(root, target)
        entry = meta_by_id.get(repo_id)
        repositories.append(
            {
                "repo_id": repo_id,
                "tree_hash": entry.tree_hash if entry else None,
                "indexer_version": entry.indexer_version if entry else INDEXER_VERSION,
                "source_sha": entry.source_sha if entry else None,
                "source_repo": entry.source_repo if entry else None,
                "chunk_count": entry.chunk_count if entry else 0,
            }
        )

    manifest = PackManifest(
        format_version=1,
        repomind_version=__version__,
        indexer_version=INDEXER_VERSION,
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        repositories=repositories,
        billed_usd=0.0,
    )
    (work / MANIFEST_NAME).write_text(
        json.dumps(asdict(manifest), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    if not as_tarball:
        return work

    archive = destination if str(destination).endswith(".tar.gz") else Path(str(destination) + ".tar.gz")
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(work, arcname=work.name)
    shutil.rmtree(work)
    return archive


def unpack_catalog(source: Path, destination: Path) -> PackManifest:
    """Load a pack directory or tarball into ``destination`` and return the manifest."""
    source = source.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    if source.is_file() and (
        source.name.endswith(".tar.gz") or source.suffixes[-2:] == [".tar", ".gz"]
    ):
        with tarfile.open(source, "r:gz") as handle:
            handle.extractall(destination, filter="data")
        # tarball contains one top directory
        children = [p for p in destination.iterdir() if p.is_dir()]
        root = children[0] if len(children) == 1 else destination
    elif source.is_dir():
        if destination != source:
            _copy_tree(source, destination)
            root = destination
        else:
            root = source
    else:
        raise FileNotFoundError(f"pack not found: {source}")

    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        # search one level down
        for child in root.iterdir():
            candidate = child / MANIFEST_NAME
            if candidate.is_file():
                manifest_path = candidate
                root = child
                break
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing {MANIFEST_NAME} under {source}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PackManifest(
        format_version=int(payload["format_version"]),
        repomind_version=str(payload["repomind_version"]),
        indexer_version=str(payload["indexer_version"]),
        created_at=str(payload["created_at"]),
        repositories=list(payload.get("repositories") or []),
        billed_usd=float(payload.get("billed_usd", 0.0)),
    )

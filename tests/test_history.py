"""Path history: committed snapshots first, optional local git fallback."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repomind.catalog import MINI_REPO_ID, catalog_roots
from repomind.history import (
    SNAPSHOT_RELATIVE_PATH,
    CapabilityMissing,
    GitHistoryService,
    HistoryPathNotFound,
    HistoryService,
    UnsafeHistoryPath,
    _safe_relative_path,
    clear_snapshot_cache,
)
from repomind.main import create_app


def _write_snapshot(root: Path, rows: list[dict[str, object]]) -> None:
    """Write a minimal history.jsonl under a catalog root."""
    target = root / SNAPSHOT_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    clear_snapshot_cache()


def _init_git_repo(root: Path) -> None:
    """Create a one-commit git work tree for local fallback tests."""
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "repomind-test@example.com"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "RepoMind Test"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (root / "app").mkdir()
    target = root / "app" / "main.py"
    target.write_text("def create_app():\n    return {}\n", encoding="utf-8")
    subprocess.run(["git", "add", "app/main.py"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed create_app"],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def snapshot_fixture(tmp_path: Path) -> Path:
    """Catalog-shaped root with a committed history snapshot (no git)."""
    root = tmp_path / "mini"
    root.mkdir()
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text(
        "def create_app():\n    return {}\n", encoding="utf-8"
    )
    _write_snapshot(
        root,
        [
            {
                "path": "app/main.py",
                "mode": "log",
                "sha": "a" * 40,
                "summary": "committed fixture history snapshot",
                "author": "RepoMind Snapshot",
                "committed_at": "2026-01-01T00:00:00Z",
            },
            {
                "path": "app/main.py",
                "mode": "blame",
                "sha": "a" * 40,
                "summary": "committed fixture history snapshot",
                "author": "RepoMind Snapshot",
                "committed_at": "2026-01-01T00:00:00Z",
                "line": 1,
            },
            {
                "path": "app/main.py",
                "mode": "blame",
                "sha": "a" * 40,
                "summary": "committed fixture history snapshot",
                "author": "RepoMind Snapshot",
                "committed_at": "2026-01-01T00:00:00Z",
                "line": 2,
            },
        ],
    )
    return root


@pytest.fixture
def git_fixture(tmp_path: Path) -> Path:
    """Catalog-shaped git fixture root without a snapshot (local fallback)."""
    root = tmp_path / "mini"
    root.mkdir()
    _init_git_repo(root)
    return root


def test_safe_path_rejects_traversal_and_absolute_forms() -> None:
    """History paths are repository-relative identifiers, never filesystem selectors."""
    with pytest.raises(UnsafeHistoryPath):
        _safe_relative_path("../etc/passwd")
    with pytest.raises(UnsafeHistoryPath):
        _safe_relative_path("/etc/passwd")
    with pytest.raises(UnsafeHistoryPath):
        _safe_relative_path("C:\\Windows\\system32")
    with pytest.raises(UnsafeHistoryPath):
        _safe_relative_path("")
    assert _safe_relative_path("app/main.py") == "app/main.py"


def test_snapshot_log_without_git(
    snapshot_fixture: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Committed snapshot answers history with no git binary on PATH."""
    monkeypatch.setattr("repomind.history.shutil.which", lambda _name: None)
    service = HistoryService({MINI_REPO_ID: snapshot_fixture})

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="log", limit=5)

    assert result.source == "snapshot"
    assert result.repo_id == MINI_REPO_ID
    assert result.path == "app/main.py"
    assert len(result.entries) == 1
    assert result.entries[0].summary == "committed fixture history snapshot"
    assert result.entries[0].sha == "a" * 40


def test_snapshot_blame_returns_line_attribution(snapshot_fixture: Path) -> None:
    """Blame rows from the snapshot are line-oriented."""
    service = HistoryService({MINI_REPO_ID: snapshot_fixture})

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="blame", limit=2)

    assert result.mode == "blame"
    assert result.source == "snapshot"
    assert result.entries[0].line == 1
    assert len(result.entries) == 2


def test_unknown_path_is_not_found(snapshot_fixture: Path) -> None:
    """A well-formed path that names no file is HistoryPathNotFound (HTTP 404)."""
    service = HistoryService({MINI_REPO_ID: snapshot_fixture})

    with pytest.raises(HistoryPathNotFound):
        service.history(repo_id=MINI_REPO_ID, path="app/missing.py")


def test_no_snapshot_and_no_git_is_capability_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Roots without a snapshot and without git degrade explicitly."""
    root = tmp_path / "plain"
    root.mkdir()
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("def create_app():\n    return {}\n", encoding="utf-8")
    monkeypatch.setattr("repomind.history.shutil.which", lambda _name: None)
    service = HistoryService({MINI_REPO_ID: root})

    with pytest.raises(CapabilityMissing) as raised:
        service.history(repo_id=MINI_REPO_ID, path="app/main.py")

    assert raised.value.reason == "git_not_found"


def test_git_fallback_when_snapshot_absent(git_fixture: Path) -> None:
    """Local stand-alone git roots without a snapshot still answer via git."""
    if shutil.which("git") is None:
        pytest.skip("git not on PATH")
    service = GitHistoryService({MINI_REPO_ID: git_fixture})

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="log", limit=5)

    assert result.source == "git"
    assert result.entries[0].summary == "seed create_app"
    assert len(result.entries[0].sha) == 40


def test_http_history_log_from_snapshot(snapshot_fixture: Path) -> None:
    """HTTP history returns 200 entries from a committed snapshot."""
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: snapshot_fixture}),
        history_service=HistoryService({MINI_REPO_ID: snapshot_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "app/main.py", "mode": "log"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["entries"][0]["summary"] == "committed fixture history snapshot"
    assert body["path"] == "app/main.py"


def test_http_history_unknown_path_is_404(snapshot_fixture: Path) -> None:
    """Missing file under a catalog root is 404, not 400 or 503."""
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: snapshot_fixture}),
        history_service=HistoryService({MINI_REPO_ID: snapshot_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "app/nope.py"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "path not found in catalog repository"


def test_http_history_rejects_path_escape(snapshot_fixture: Path) -> None:
    """History cannot be turned into a filesystem probe."""
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: snapshot_fixture}),
        history_service=HistoryService({MINI_REPO_ID: snapshot_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "../secrets"},
        )

    assert response.status_code == 400


def test_packaged_fixtures_serve_history_without_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default catalog fixtures ship snapshots; history is 200 with no git."""
    monkeypatch.setattr("repomind.history.shutil.which", lambda _name: None)
    roots = catalog_roots(allow_environment=False)
    service = HistoryService(roots)

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="log")

    assert result.source == "snapshot"
    assert result.entries
    assert result.entries[0].author == "RepoMind Snapshot"


def test_http_packaged_mini_history_is_200() -> None:
    """Default app answers GET /v1/code/history for the mini fixture."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": "mini", "path": "app/main.py", "mode": "log"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["repo_id"] == "mini"
    assert body["entries"]
    assert body["entries"][0]["sha"]

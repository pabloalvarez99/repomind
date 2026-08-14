"""Optional read-only git history capability tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repomind.catalog import MINI_REPO_ID
from repomind.history import (
    CapabilityMissing,
    GitHistoryService,
    UnsafeHistoryPath,
    _safe_relative_path,
)
from repomind.main import create_app


def _init_git_repo(root: Path) -> None:
    """Create a one-commit git work tree for history plumbing tests."""
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
def git_fixture(tmp_path: Path) -> Path:
    """Return a catalog-shaped git fixture root."""
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


def test_log_returns_commit_metadata_for_catalog_path(git_fixture: Path) -> None:
    """A catalog root that is a git work tree can answer log without a remote."""
    service = GitHistoryService({MINI_REPO_ID: git_fixture})

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="log", limit=5)

    assert result.repo_id == MINI_REPO_ID
    assert result.path == "app/main.py"
    assert result.mode == "log"
    assert len(result.entries) == 1
    assert result.entries[0].summary == "seed create_app"
    assert len(result.entries[0].sha) == 40
    assert result.entries[0].author == "RepoMind Test"


def test_blame_returns_line_attribution(git_fixture: Path) -> None:
    """Blame is line-oriented and still confined to the catalog path."""
    service = GitHistoryService({MINI_REPO_ID: git_fixture})

    result = service.history(repo_id=MINI_REPO_ID, path="app/main.py", mode="blame", limit=2)

    assert result.mode == "blame"
    assert result.entries
    assert result.entries[0].line == 1
    assert result.entries[0].sha


def test_missing_git_is_capability_missing(
    git_fixture: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No git binary means 503-shaped capability_missing, not an empty success."""
    monkeypatch.setattr("repomind.history.shutil.which", lambda _name: None)
    service = GitHistoryService({MINI_REPO_ID: git_fixture})

    with pytest.raises(CapabilityMissing) as raised:
        service.history(repo_id=MINI_REPO_ID, path="app/main.py")

    assert raised.value.capability == "git_history"
    assert raised.value.reason == "git_not_found"


def test_non_git_catalog_root_is_capability_missing(tmp_path: Path) -> None:
    """Committed fixtures without their own .git degrade explicitly."""
    root = tmp_path / "plain"
    root.mkdir()
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("def create_app():\n    return {}\n", encoding="utf-8")
    service = GitHistoryService({MINI_REPO_ID: root})

    with pytest.raises(CapabilityMissing) as raised:
        service.history(repo_id=MINI_REPO_ID, path="app/main.py")

    assert raised.value.reason == "repository_not_git"


def test_http_history_log_on_injected_git_root(git_fixture: Path) -> None:
    """HTTP history shares the catalog validity function and returns entries."""
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: git_fixture}),
        history_service=GitHistoryService({MINI_REPO_ID: git_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "app/main.py", "mode": "log"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["entries"][0]["summary"] == "seed create_app"


def test_http_history_capability_missing_without_git(
    git_fixture: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hosted and local free paths without git advertise the gap."""
    monkeypatch.setattr("repomind.history.shutil.which", lambda _name: None)
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: git_fixture}),
        history_service=GitHistoryService({MINI_REPO_ID: git_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "app/main.py"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "capability_missing",
        "capability": "git_history",
        "reason": "git_not_found",
    }


def test_http_history_rejects_path_escape(git_fixture: Path) -> None:
    """History cannot be turned into a filesystem probe."""
    from repomind.answer import CodeAskService

    app = create_app(
        CodeAskService.from_roots({MINI_REPO_ID: git_fixture}),
        history_service=GitHistoryService({MINI_REPO_ID: git_fixture}),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/code/history",
            params={"repo_id": MINI_REPO_ID, "path": "../secrets"},
        )

    assert response.status_code == 400


def test_default_catalog_fixtures_report_not_git_when_git_exists() -> None:
    """Packaged fixtures are not stand-alone git repos; history says so.

    Hosted Vercel deploys typically have no .git either — same capability_missing
    contract, never a fabricated history.
    """
    if shutil.which("git") is None:
        pytest.skip("git not on PATH")
    from repomind.catalog import catalog_roots

    roots = catalog_roots(allow_environment=False)
    service = GitHistoryService(roots)

    with pytest.raises(CapabilityMissing) as raised:
        service.history(repo_id=MINI_REPO_ID, path="app/main.py")

    assert raised.value.reason == "repository_not_git"

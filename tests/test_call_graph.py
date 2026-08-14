"""Python AST incoming refs (who calls X) over catalog fixtures."""

from __future__ import annotations

from fastapi.testclient import TestClient

from repomind.answer import CodeAskService
from repomind.catalog import MINI_REPO_ID, catalog_roots
from repomind.main import create_app


def test_create_app_has_at_least_one_caller() -> None:
    """Golden: a known function is called from the fixture (boot → create_app)."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))

    refs = service.incoming_refs(repo_id=MINI_REPO_ID, symbol="create_app")

    assert refs.qualname == "create_app"
    assert len(refs.callers) >= 1
    assert any(site.caller_qualname == "boot" for site in refs.callers)
    assert all(site.path.endswith(".py") for site in refs.callers)
    assert all(site.line >= 1 for site in refs.callers)


def test_leaf_function_may_have_zero_callers_without_lying() -> None:
    """Golden: health is a leaf — empty callers is honest, not a failure."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))

    refs = service.incoming_refs(repo_id=MINI_REPO_ID, symbol="health")

    assert refs.qualname == "health"
    assert refs.callers == []


def test_http_refs_returns_call_sites() -> None:
    """GET /v1/code/refs exposes the same fixture-only call graph."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/v1/code/refs",
            params={"repo_id": "mini", "symbol": "create_app"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["repo_id"] == "mini"
    assert body["qualname"] == "create_app"
    assert len(body["callers"]) >= 1
    assert body["callers"][0]["path"] == "app/main.py"


def test_http_refs_leaf_is_empty_not_503() -> None:
    """Zero callers is 200 with an empty list, never capability_missing."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/v1/code/refs",
            params={"repo_id": "mini", "symbol": "health"},
        )

    assert response.status_code == 200
    assert response.json()["callers"] == []


def test_refs_console_renders_callers() -> None:
    """UI /refs shows path:line call sites for a known symbol."""
    with TestClient(create_app()) as client:
        response = client.get("/refs", params={"repo_id": "mini", "symbol": "create_app"})

    assert response.status_code == 200
    text = response.text
    assert "Who calls" in text
    assert "app/main.py:" in text
    assert "boot" in text

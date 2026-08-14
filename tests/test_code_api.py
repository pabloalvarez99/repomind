"""Code-question HTTP contract tests."""

import re

from fastapi.testclient import TestClient

from repomind.main import create_app


def test_ask_locates_create_app_with_path_line_citations() -> None:
    """The canonical P4 question is grounded in the fixture source."""
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/code/ask",
            json={"question": "Where is create_app defined?", "repo_id": "mini"},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "citations"}
    assert "`create_app`" in body["answer"]
    assert body["citations"][0]["path"] == "app/main.py"
    assert body["citations"][0]["start_line"] == 6
    assert body["citations"][0]["end_line"] == 9
    assert "def create_app" in body["citations"][0]["snippet"]
    assert len(body["citations"]) == 1


def test_ask_refuses_when_no_code_evidence_matches() -> None:
    """Unknown concepts produce no fabricated citation."""
    with TestClient(create_app()) as client:
        body = client.post(
            "/v1/code/ask", json={"question": "Who won Antarctic chess?"}
        ).json()

    assert "could not find code evidence" in body["answer"]
    assert body["citations"] == []


def test_unknown_repository_id_is_not_treated_as_a_path() -> None:
    """The public id selects a catalog entry and cannot traverse the filesystem."""
    with TestClient(create_app()) as client:
        unknown = client.post(
            "/v1/code/ask",
            json={"question": "Where is create_app?", "repo_id": "unknown"},
        )
        traversal = client.post(
            "/v1/code/ask",
            json={"question": "Where is create_app?", "repo_id": "../../etc"},
        )

    assert unknown.status_code == 404
    assert traversal.status_code == 422


def test_blank_question_is_rejected() -> None:
    """Whitespace-only input never reaches retrieval."""
    with TestClient(create_app()) as client:
        response = client.post("/v1/code/ask", json={"question": "   "})

    assert response.status_code == 422


def test_openapi_contains_the_exact_code_ask_route() -> None:
    """The planned API surface remains discoverable."""
    with TestClient(create_app()) as client:
        document = client.get("/openapi.json").json()

    assert "/v1/code/ask" in document["paths"]
    assert "post" in document["paths"]["/v1/code/ask"]


def test_symbols_returns_a_deterministic_outline() -> None:
    """The catalog exposes source navigation without source text execution."""
    with TestClient(create_app()) as client:
        first = client.get("/v1/code/symbols", params={"repo_id": "mini"})
        second = client.get("/v1/code/symbols", params={"repo_id": "mini"})

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()[0] == {
        "path": "app/main.py",
        "qualname": "create_app",
        "start_line": 6,
        "end_line": 9,
        "kind": "function",
    }


def test_symbols_rejects_unknown_repository_id() -> None:
    """Outline lookup obeys the same closed catalog boundary as questions."""
    with TestClient(create_app()) as client:
        response = client.get("/v1/code/symbols", params={"repo_id": "unknown"})

    assert response.status_code == 404


def test_console_is_accessible_and_has_no_cdn_dependency() -> None:
    """The free-path UI exposes labeled controls and only local assets."""
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert '<label for="repo_id">' in response.text
    assert '<label for="question">' in response.text
    assert 'value="mini"' in response.text
    assert 'value="production_rag"' in response.text
    assert "https://" not in response.text


def test_console_renders_path_line_evidence_and_request_id() -> None:
    """A UI answer displays the same grounded evidence as the JSON API."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/ask",
            params={"question": "Where is run_query defined?", "repo_id": "production_rag"},
        )

    assert response.status_code == 200
    assert "production_rag/query_pipeline.py:220-250" in response.text
    request_id = response.headers["x-request-id"]
    assert re.fullmatch(r"[0-9a-f-]{36}", request_id)
    assert f"request_id <code>{request_id}</code>" in response.text
    assert re.search(r">\s*cited\s*<", response.text)


def test_console_renders_an_explicit_refusal() -> None:
    """The browser path makes missing evidence visible without citations."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/ask",
            params={"question": "Where is QuantumDatabaseRouter?", "repo_id": "mini"},
        )

    assert response.status_code == 200
    assert re.search(r">\s*refused\s*<", response.text)
    assert "will not manufacture an answer" in response.text
    assert "copy-location" not in response.text


def test_console_offers_a_copy_button_per_path_line_citation() -> None:
    """Each citation carries a copyable path:line that matches the rendered code."""
    with TestClient(create_app()) as client:
        response = client.get(
            "/ask",
            params={"question": "Where is create_app defined?", "repo_id": "mini"},
        )

    assert response.status_code == 200
    locations = re.findall(r'<code class="location">([^<]+)</code>', response.text)
    copyable = re.findall(r'class="copy-location" data-copy="([^"]+)"', response.text)
    assert locations == copyable
    assert "app/main.py:6-9" in copyable
    # Ships hidden so a browser without JavaScript never shows a dead control.
    assert response.text.count("hidden>copy</button>") == len(copyable)


def test_console_copy_enhancement_is_local_and_progressive() -> None:
    """The clipboard script is served from the package, never from a CDN."""
    with TestClient(create_app()) as client:
        page = client.get("/")
        script = client.get("/static/app.js")

    assert 'src="http://testserver/static/app.js" defer' in page.text
    assert script.status_code == 200
    assert "navigator.clipboard" in script.text
    assert "https://" not in script.text

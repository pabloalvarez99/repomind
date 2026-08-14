"""Code-question HTTP contract tests."""

import re

import pytest
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


def test_post_accepts_the_catalog_id_that_contains_an_underscore() -> None:
    """``production_rag`` is an id the catalog publishes, so POST must take it.

    It used to 422 on a slug-shaped pattern while GET /ask answered the same id,
    which made the JSON API disagree with the browser about what exists.
    """
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/code/ask",
            json={"question": "Where is run_query defined?", "repo_id": "production_rag"},
        )

    assert response.status_code == 200
    citation = response.json()["citations"][0]
    assert citation["path"] == "production_rag/query_pipeline.py"
    assert citation["start_line"] == 220


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
        empty = client.post(
            "/v1/code/ask",
            json={"question": "Where is create_app?", "repo_id": ""},
        )
        blank = client.post(
            "/v1/code/ask",
            json={"question": "Where is create_app?", "repo_id": "   "},
        )

    assert unknown.status_code == 404
    assert traversal.status_code == 400
    assert empty.status_code == 422
    assert blank.status_code == 422


@pytest.mark.parametrize(
    "repo_id",
    ["../../etc", "..", "/etc/passwd", "mini/../mini", "C:\\Windows", "mini\x00", "a" * 65],
)
def test_path_shaped_repository_ids_are_rejected_before_any_lookup(repo_id: str) -> None:
    """Nothing that could name a filesystem location reaches the catalog."""
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/code/ask", json={"question": "Where is create_app?", "repo_id": repo_id}
        )

    assert response.status_code == 400


@pytest.mark.parametrize("repo_id", ["mini", "production_rag"])
def test_every_surface_agrees_on_a_catalog_id(repo_id: str) -> None:
    """POST, the console, and the symbols outline share one validity function."""
    with TestClient(create_app()) as client:
        posted = client.post(
            "/v1/code/ask", json={"question": "Where is create_app?", "repo_id": repo_id}
        )
        console = client.get(
            "/ask", params={"question": "Where is create_app?", "repo_id": repo_id}
        )
        symbols = client.get("/v1/code/symbols", params={"repo_id": repo_id})

    assert (posted.status_code, console.status_code, symbols.status_code) == (200, 200, 200)


@pytest.mark.parametrize(("repo_id", "expected"), [("unknown", 404), ("../../etc", 400)])
def test_every_surface_rejects_a_bad_id_with_the_same_status(
    repo_id: str, expected: int
) -> None:
    """A bad id cannot be legal on one door and rejected on the next."""
    with TestClient(create_app()) as client:
        posted = client.post(
            "/v1/code/ask", json={"question": "Where is create_app?", "repo_id": repo_id}
        )
        console = client.get(
            "/ask", params={"question": "Where is create_app?", "repo_id": repo_id}
        )
        symbols = client.get("/v1/code/symbols", params={"repo_id": repo_id})

    assert posted.status_code == expected
    assert console.status_code == expected
    assert symbols.status_code == expected


def test_blank_question_is_rejected() -> None:
    """Whitespace-only input never reaches retrieval."""
    with TestClient(create_app()) as client:
        response = client.post("/v1/code/ask", json={"question": "   "})

    assert response.status_code == 422


def test_catalog_lists_every_repository_with_its_content_address() -> None:
    """A caller can see what this instance indexes without guessing an id."""
    with TestClient(create_app()) as client:
        response = client.get("/v1/catalog")

    assert response.status_code == 200
    entries = response.json()
    assert [entry["repo_id"] for entry in entries] == ["mini", "production_rag"]
    for entry in entries:
        assert set(entry) == {
            "repo_id",
            "file_count",
            "indexed_file_count",
            "chunk_count",
            "tree_hash",
            "indexer_version",
        }
        assert len(entry["tree_hash"]) == 64
        assert entry["indexed_file_count"] <= entry["file_count"]
        assert entry["chunk_count"] > 0


def test_catalog_is_stable_across_requests() -> None:
    """The tree hash addresses committed bytes, so it cannot drift per request."""
    with TestClient(create_app()) as client:
        first = client.get("/v1/catalog").json()
        second = client.get("/v1/catalog").json()

    assert first == second


def test_catalog_takes_no_arguments_that_could_name_a_path() -> None:
    """The route that says what exists is not a place to ask for something else."""
    with TestClient(create_app()) as client:
        document = client.get("/openapi.json").json()

    assert document["paths"]["/v1/catalog"]["get"].get("parameters", []) == []


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

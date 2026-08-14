"""In-memory symbol and lexical retrieval tests."""

from pathlib import Path

from repomind.index import InMemoryCodeIndex
from repomind.ingest.chunk_python import chunk_repository

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mini_repo"


def build_index() -> InMemoryCodeIndex:
    """Build the fixture index through the real walk and AST path."""
    return InMemoryCodeIndex(chunk_repository(FIXTURE))


def test_locate_create_app_returns_the_exact_path_and_lines() -> None:
    """The milestone's canonical locate query resolves exactly."""
    index = build_index()

    results = index.search("Where is create_app defined?")

    assert results
    assert results[0].chunk.chunk_id == "app/main.py::create_app"
    assert results[0].chunk.path == "app/main.py"
    assert results[0].chunk.start_line == 6
    assert results[0].chunk.end_line == 9


def test_exact_symbol_lookup_supports_method_leaf_names() -> None:
    """A method can be found by its leaf or fully qualified name."""
    index = build_index()

    by_leaf = index.locate_symbol("greet")
    by_qualified_name = index.locate_symbol("GreetingService.greet")

    assert by_leaf == by_qualified_name
    assert by_leaf[0].chunk_id == "app/service.py::GreetingService.greet"


def test_token_overlap_finds_the_service_without_an_exact_symbol() -> None:
    """Prose still retrieves code when it names behavior instead of a symbol."""
    results = build_index().search("Which code renders a greeting prefix?")

    assert results
    assert results[0].chunk.path == "app/service.py"
    assert "greeting" in results[0].matched_terms


def test_unrelated_question_has_no_results() -> None:
    """The index does not manufacture relevance for unknown terms."""
    assert build_index().search("quarterly Antarctic revenue") == ()


def test_search_rejects_a_non_positive_limit() -> None:
    """An invalid retrieval bound fails before work begins."""
    try:
        build_index().search("create_app", limit=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("non-positive limit was accepted")

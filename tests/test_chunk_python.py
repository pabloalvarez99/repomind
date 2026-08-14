"""AST chunk contract tests."""

from pathlib import Path

from repomind.ingest.chunk_python import chunk_repository

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mini_repo"


def test_chunk_ids_and_lines_come_from_the_ast() -> None:
    """Definitions carry stable ids and exact source boundaries."""
    chunks = {chunk.chunk_id: chunk for chunk in chunk_repository(FIXTURE)}

    create_app = chunks["app/main.py::create_app"]
    assert create_app.path == "app/main.py"
    assert create_app.qualname == "create_app"
    assert create_app.kind == "function"
    assert create_app.start_line == 6
    assert create_app.end_line == 9
    assert create_app.text.startswith("def create_app()")
    assert "return" in create_app.text


def test_methods_use_qualified_names() -> None:
    """Two classes may define the same method without colliding in the index."""
    chunks = {chunk.chunk_id: chunk for chunk in chunk_repository(FIXTURE)}

    greeting = chunks["app/service.py::GreetingService"]
    greet = chunks["app/service.py::GreetingService.greet"]
    assert greeting.kind == "class"
    assert greet.qualname == "GreetingService.greet"
    assert greet.start_line > greeting.start_line
    assert greet.end_line <= greeting.end_line


def test_gitignored_python_never_becomes_a_chunk() -> None:
    """The chunker consumes the safe walker rather than rediscovering files."""
    chunk_ids = {chunk.chunk_id for chunk in chunk_repository(FIXTURE)}

    assert all("must_not_be_indexed" not in chunk_id for chunk_id in chunk_ids)
    assert all("generated_symbol" not in chunk_id for chunk_id in chunk_ids)

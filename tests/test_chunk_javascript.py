"""Free-path JavaScript/TypeScript chunking tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from repomind.answer import CodeAskService
from repomind.catalog import MINI_JS_REPO_ID, catalog_roots
from repomind.ingest import (
    IncrementalIngestor,
    chunk_javascript_source,
    try_chunk_with_treesitter,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mini_js"


def test_free_path_finds_exported_function_foo() -> None:
    """The canonical JS golden is a path:line hit for foo, not a language claim."""
    source = (FIXTURE / "src" / "foo.js").read_text(encoding="utf-8")
    chunks = chunk_javascript_source(source, path="src/foo.js")
    by_name = {chunk.qualname: chunk for chunk in chunks}

    assert "foo" in by_name
    assert by_name["foo"].kind == "function"
    assert by_name["foo"].path == "src/foo.js"
    assert by_name["foo"].start_line >= 1
    assert by_name["foo"].end_line >= by_name["foo"].start_line
    assert "export function foo" in by_name["foo"].text
    assert len(by_name["foo"].content_hash) == 64


def test_free_path_indexes_typescript_class_and_async_function() -> None:
    """TypeScript uses the same free-path scanner; methods stay nested in the class."""
    source = (FIXTURE / "src" / "util.ts").read_text(encoding="utf-8")
    chunks = chunk_javascript_source(source, path="src/util.ts")
    names = {chunk.qualname: chunk for chunk in chunks}

    assert names["Counter"].kind == "class"
    assert names["loadConfig"].kind == "async_function"
    assert "next" not in names  # nested methods are not separate top-level chunks


def test_service_answers_where_is_foo_defined_with_path_line() -> None:
    """POST-shaped ask against mini_js cites the fixture definition."""
    service = CodeAskService.from_roots(catalog_roots(allow_environment=False))

    answer = service.ask("Where is foo defined?", repo_id=MINI_JS_REPO_ID)

    assert answer.citations
    assert answer.citations[0].path == "src/foo.js"
    assert answer.citations[0].start_line >= 1
    assert "`foo`" in answer.answer


def test_incremental_ingest_indexes_js_and_reuses_unchanged_bytes() -> None:
    """JS files participate in the content-addressed cache like Python."""
    ingestor = IncrementalIngestor(FIXTURE)
    first = ingestor.ingest()
    second = ingestor.ingest()

    assert first.stats.parsed_files >= 2
    assert second.stats.is_noop
    assert any(chunk.qualname == "foo" for chunk in first.snapshot.chunks)
    assert first.snapshot.indexed_file_count >= 2


@pytest.mark.treesitter
def test_optional_treesitter_path_when_extra_installed() -> None:
    """Grammar path is optional; default CI never downloads it."""
    pytest.importorskip("tree_sitter")
    pytest.importorskip("tree_sitter_javascript")
    source = (FIXTURE / "src" / "foo.js").read_text(encoding="utf-8")
    chunks = try_chunk_with_treesitter(source, path="src/foo.js")
    assert chunks is not None
    assert any(chunk.qualname == "foo" for chunk in chunks)


def test_treesitter_helper_returns_none_without_extra() -> None:
    """Without the optional extra the free path remains the only active scanner."""
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_javascript  # noqa: F401
    except ImportError:
        source = "export function foo() { return 1; }\n"
        assert try_chunk_with_treesitter(source, path="x.js") is None
        return
    pytest.skip("treesitter extra is installed in this environment")

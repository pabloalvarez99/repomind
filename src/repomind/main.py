"""FastAPI application, operational endpoint, and code-question API."""

import json
import logging
import time
from collections.abc import Awaitable, Callable
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.responses import Response

from repomind import __version__
from repomind.answer import (
    CodeAnswer,
    CodeAskService,
    CodeSymbol,
    HistoryEntryModel,
    HistoryResponse,
    IncomingRefsResponse,
    RepositoryMetadata,
)
from repomind.catalog import (
    MINI_REPO_ID,
    BlankRepositoryId,
    MalformedRepositoryId,
    UnknownRepository,
    catalog_ids,
    catalog_roots,
    mini_root,
)
from repomind.history import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    CapabilityMissing,
    GitHistoryService,
    HistoryMode,
    HistoryPathNotFound,
    HistoryService,
    UnsafeHistoryPath,
)

SERVICE_NAME = "repomind"
LOGGER = logging.getLogger("repomind.http")


class HealthResponse(BaseModel):
    """Liveness response for the process."""

    status: Literal["ok"] = "ok"
    service: str = SERVICE_NAME
    version: str = __version__


class CodeAskRequest(BaseModel):
    """A code question scoped to a configured repository."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2_000)
    # No shape pattern here: a repo_id is an identifier the catalog hands out, and
    # the catalog already publishes one -- ``production_rag`` -- that no slug regex
    # accepts. Membership is decided by repomind.catalog.validate_repo_id, which
    # every other surface uses too, including the 64-character bound. Only
    # emptiness is a schema concern, because an absent id is not a wrong id.
    repo_id: str = Field(default=MINI_REPO_ID, min_length=1)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only questions before index work."""
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


fixture_root = mini_root
"""Backward-compatible name for the original mini fixture root."""


def _package_path(name: str) -> Path:
    """Return an installed package asset directory."""
    return Path(str(files("repomind").joinpath(name)))


def create_app(
    service: CodeAskService | None = None,
    *,
    history_service: HistoryService | GitHistoryService | None = None,
) -> FastAPI:
    """Build an isolated API application over an injectable code service."""
    roots = catalog_roots()
    code_service = CodeAskService.from_roots(roots) if service is None else service
    path_history = (
        HistoryService(roots) if history_service is None else history_service
    )
    app = FastAPI(
        title="RepoMind",
        version=__version__,
        description="Offline codebase Q&A with AST-aware path:line citations.",
        license_info={"name": "MIT", "identifier": "MIT"},
    )
    templates = Jinja2Templates(directory=_package_path("templates"))
    app.mount("/static", StaticFiles(directory=_package_path("static")), name="static")

    # One mapping from the one validity function, so every surface answers a bad
    # id with the same status: nothing sent is 422, path-shaped is 400 (the caller
    # tried something the catalog will never serve), well formed but absent is 404.
    def _repo_id_error(status_code: int, detail: str) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail})

    @app.exception_handler(BlankRepositoryId)
    async def _blank_repo_id(request: Request, error: Exception) -> JSONResponse:
        """Answer a missing repository id as a request-validation failure."""
        return _repo_id_error(422, "repository id must not be blank")

    @app.exception_handler(MalformedRepositoryId)
    async def _malformed_repo_id(request: Request, error: Exception) -> JSONResponse:
        """Answer a path-shaped repository id without revealing what exists."""
        return _repo_id_error(400, "repository id is not a catalog identifier")

    @app.exception_handler(UnknownRepository)
    async def _unknown_repo_id(request: Request, error: Exception) -> JSONResponse:
        """Answer a well-formed id that names nothing in the closed catalog."""
        return _repo_id_error(404, "repository id is not configured")

    @app.exception_handler(CapabilityMissing)
    async def _capability_missing(request: Request, error: Exception) -> JSONResponse:
        """Optional surfaces degrade with an explicit missing-capability payload."""
        missing = error if isinstance(error, CapabilityMissing) else CapabilityMissing(
            "unknown", "unknown"
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "capability_missing",
                "capability": missing.capability,
                "reason": missing.reason,
            },
        )

    @app.exception_handler(UnsafeHistoryPath)
    async def _unsafe_history_path(request: Request, error: Exception) -> JSONResponse:
        """History paths are catalog-relative only; escape attempts are 400."""
        return _repo_id_error(400, "path is not a catalog-relative file")

    @app.exception_handler(HistoryPathNotFound)
    async def _history_path_not_found(request: Request, error: Exception) -> JSONResponse:
        """Well-formed path that names no file in the catalog root is 404."""
        return _repo_id_error(404, "path not found in catalog repository")

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attach a correlation id and emit one structured completion event."""
        request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        LOGGER.info(
            json.dumps(
                {
                    "event": "http_request_complete",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1_000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response

    def _console_context(**extra: object) -> dict[str, object]:
        """Shared template context: closed catalog metadata always visible."""
        context: dict[str, object] = {
            "repo_ids": catalog_ids(),
            "catalog": code_service.catalog(),
        }
        context.update(extra)
        return context

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def ask_console(request: Request) -> HTMLResponse:
        """Render the credential-free repository ask console."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_console_context(),
        )

    @app.get("/ask", response_class=HTMLResponse, include_in_schema=False)
    def ask_from_console(
        request: Request,
        question: str = Query(min_length=1, max_length=2_000),
        repo_id: str = Query(default=MINI_REPO_ID),
    ) -> HTMLResponse:
        """Render one grounded answer or refusal with a trace id."""
        result = code_service.ask(question, repo_id=repo_id)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_console_context(
                selected_repo=repo_id,
                question=question,
                result=result,
                request_id=request.state.request_id,
            ),
        )

    @app.get("/refs", response_class=HTMLResponse, include_in_schema=False)
    def refs_console(
        request: Request,
        symbol: str = Query(min_length=1, max_length=256),
        repo_id: str = Query(default=MINI_REPO_ID),
    ) -> HTMLResponse:
        """Render incoming Python call sites for one symbol in a catalog repo."""
        refs = code_service.incoming_refs(repo_id=repo_id, symbol=symbol)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_console_context(
                selected_repo=repo_id,
                refs_symbol=symbol,
                refs=refs,
                request_id=request.state.request_id,
            ),
        )

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        """Report that the API process is alive."""
        return HealthResponse()

    @app.get("/v1/catalog", response_model=list[RepositoryMetadata], tags=["code"])
    def catalog() -> list[RepositoryMetadata]:
        """List every repository this instance serves, with its content address.

        Takes no arguments on purpose. The catalog is the answer to "what can I
        ask about", so it cannot also be a place to name something it does not
        already hold.
        """
        return code_service.catalog()

    @app.post("/v1/code/ask", response_model=CodeAnswer, tags=["code"])
    def ask_code(request: CodeAskRequest) -> CodeAnswer:
        """Answer from indexed definitions, or return an evidence-free refusal."""
        return code_service.ask(request.question, repo_id=request.repo_id)

    @app.get("/v1/code/symbols", response_model=list[CodeSymbol], tags=["code"])
    def code_symbols(repo_id: str = MINI_REPO_ID) -> list[CodeSymbol]:
        """Return a deterministic AST outline for a catalog repository."""
        return code_service.symbols(repo_id=repo_id)

    @app.get("/v1/code/refs", response_model=IncomingRefsResponse, tags=["code"])
    def code_refs(
        symbol: str = Query(min_length=1, max_length=256),
        repo_id: str = MINI_REPO_ID,
    ) -> IncomingRefsResponse:
        """Return Python AST incoming call sites for one symbol (fixture-only).

        Zero callers is a leaf, not an error. Unknown symbols also return an
        empty caller list rather than inventing edges.
        """
        return code_service.incoming_refs(repo_id=repo_id, symbol=symbol)

    @app.get("/v1/code/history", response_model=HistoryResponse, tags=["code"])
    def code_history(
        repo_id: str = MINI_REPO_ID,
        path: str = Query(min_length=1, max_length=512),
        mode: HistoryMode = "log",
        limit: int = Query(default=DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
    ) -> HistoryResponse:
        """Return read-only log or blame for one path inside a catalog repo.

        Packaged fixtures answer from a committed ``.repomind/history.jsonl``
        snapshot (no ``git(1)`` required). Roots without a snapshot may fall
        back to local git. Missing both is ``503 capability_missing``. There is
        no remote, clone, or upload surface.
        """
        result = path_history.history(
            repo_id=repo_id, path=path, mode=mode, limit=limit
        )
        return HistoryResponse(
            repo_id=result.repo_id,
            path=result.path,
            mode=result.mode,
            entries=[
                HistoryEntryModel(
                    sha=entry.sha,
                    summary=entry.summary,
                    author=entry.author,
                    committed_at=entry.committed_at,
                    line=entry.line,
                )
                for entry in result.entries
            ],
        )

    return app


app = create_app()

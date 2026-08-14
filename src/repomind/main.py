"""FastAPI application, operational endpoint, and code-question API."""

import json
import logging
import time
from collections.abc import Awaitable, Callable
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.responses import Response

from repomind import __version__
from repomind.answer import CodeAnswer, CodeAskService, CodeSymbol, UnknownRepository
from repomind.catalog import REPOSITORY_IDS, catalog_roots, mini_root

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
    repo_id: str = Field(default="mini", min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")

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


def create_app(service: CodeAskService | None = None) -> FastAPI:
    """Build an isolated API application over an injectable code service."""
    code_service = CodeAskService.from_roots(catalog_roots()) if service is None else service
    app = FastAPI(
        title="RepoMind",
        version=__version__,
        description="Offline codebase Q&A with AST-aware path:line citations.",
        license_info={"name": "MIT", "identifier": "MIT"},
    )
    templates = Jinja2Templates(directory=_package_path("templates"))
    app.mount("/static", StaticFiles(directory=_package_path("static")), name="static")

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

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def ask_console(request: Request) -> HTMLResponse:
        """Render the credential-free repository ask console."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"repo_ids": REPOSITORY_IDS},
        )

    @app.get("/ask", response_class=HTMLResponse, include_in_schema=False)
    def ask_from_console(
        request: Request,
        question: str = Query(min_length=1, max_length=2_000),
        repo_id: str = Query(default="mini"),
    ) -> HTMLResponse:
        """Render one grounded answer or refusal with a trace id."""
        try:
            result = code_service.ask(question, repo_id=repo_id)
        except UnknownRepository as error:
            raise HTTPException(
                status_code=404, detail="repository id is not configured"
            ) from error
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "repo_ids": REPOSITORY_IDS,
                "selected_repo": repo_id,
                "question": question,
                "result": result,
                "request_id": request.state.request_id,
            },
        )

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        """Report that the API process is alive."""
        return HealthResponse()

    @app.post("/v1/code/ask", response_model=CodeAnswer, tags=["code"])
    def ask_code(request: CodeAskRequest) -> CodeAnswer:
        """Answer from indexed definitions, or return an evidence-free refusal."""
        try:
            return code_service.ask(request.question, repo_id=request.repo_id)
        except UnknownRepository as error:
            raise HTTPException(
                status_code=404, detail="repository id is not configured"
            ) from error

    @app.get("/v1/code/symbols", response_model=list[CodeSymbol], tags=["code"])
    def code_symbols(repo_id: str = "mini") -> list[CodeSymbol]:
        """Return a deterministic AST outline for a catalog repository."""
        try:
            return code_service.symbols(repo_id=repo_id)
        except UnknownRepository as error:
            raise HTTPException(
                status_code=404, detail="repository id is not configured"
            ) from error

    return app


app = create_app()

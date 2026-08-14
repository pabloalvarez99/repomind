"""FastAPI application, operational endpoint, and code-question API."""

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from repomind import __version__
from repomind.answer import CodeAnswer, CodeAskService, UnknownRepository
from repomind.catalog import catalog_roots, mini_root

SERVICE_NAME = "repomind"


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


def create_app(service: CodeAskService | None = None) -> FastAPI:
    """Build an isolated API application over an injectable code service."""
    code_service = CodeAskService.from_roots(catalog_roots()) if service is None else service
    app = FastAPI(
        title="RepoMind",
        version=__version__,
        description="Offline codebase Q&A with AST-aware path:line citations.",
        license_info={"name": "MIT", "identifier": "MIT"},
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

    return app


app = create_app()

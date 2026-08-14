"""FastAPI application and operational endpoints."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from repomind import __version__

SERVICE_NAME = "repomind"


class HealthResponse(BaseModel):
    """Liveness response for the process."""

    status: Literal["ok"] = "ok"
    service: str = SERVICE_NAME
    version: str = __version__


def create_app() -> FastAPI:
    """Build an isolated API application."""
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

    return app


app = create_app()

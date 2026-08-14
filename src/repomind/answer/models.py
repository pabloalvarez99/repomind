"""Public code-question response models."""

from pydantic import BaseModel, ConfigDict, Field


class CodeCitation(BaseModel):
    """A source range supporting a code answer."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    snippet: str | None = None


class CodeAnswer(BaseModel):
    """A grounded answer, or a refusal with no citations."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    citations: list[CodeCitation]

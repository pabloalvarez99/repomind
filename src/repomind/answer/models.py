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


class CodeSymbol(BaseModel):
    """One definition in a repository's deterministic source outline."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    qualname: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    kind: str = Field(min_length=1)


class RepositoryMetadata(BaseModel):
    """What one catalog repository contains, addressably.

    ``tree_hash`` identifies the exact file set indexed, and ``indexer_version``
    identifies the rules that read it. Two instances reporting the same pair are
    answering from the same index; either one differing explains why they differ.
    """

    model_config = ConfigDict(extra="forbid")

    repo_id: str = Field(min_length=1)
    file_count: int = Field(ge=0)
    indexed_file_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    tree_hash: str = Field(min_length=1)
    indexer_version: str = Field(min_length=1)


class HistoryEntryModel(BaseModel):
    """One git log line or blame attribution on a catalog path."""

    model_config = ConfigDict(extra="forbid")

    sha: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    author: str | None = None
    committed_at: str | None = None
    line: int | None = Field(default=None, ge=1)


class HistoryResponse(BaseModel):
    """Read-only git history for one path inside a catalog repository."""

    model_config = ConfigDict(extra="forbid")

    repo_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    entries: list[HistoryEntryModel]

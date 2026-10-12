"""Explicit unknowns and version-specific provenance; fetching never grants review."""
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class Domain(StrEnum):
    employment = "Labour and employment"
    consumer = "Consumer law"
    contracts = "Contracts"
    property = "Tenancy and property"
    family = "Family law"
    procedure = "Criminal and civil procedure"
    corporate = "Corporate and tax"
    specialist = "Other specialist areas"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    title: str = Field(min_length=3, max_length=500)
    domain: Domain
    namespace: str = "official"
    topics: list[str] = Field(default_factory=list)
    instrument_type: str | None = None
    issuing_authority: str | None = None
    act_number: str | None = None
    act_year: int | None = None
    case_identifier: str | None = None
    jurisdiction: Literal["central", "state", "unknown"] = "unknown"
    states: list[str] = Field(default_factory=list)
    court: str | None = None
    official_url: str | None = None
    retrieved_at: str | None = None
    checksum: str | None = None
    source_version: str | None = None
    publication_date: date | None = None
    effective_date: date | None = None
    effective_until: date | None = None
    amends: list[str] = Field(default_factory=list)
    repeals: list[str] = Field(default_factory=list)
    supersedes: str | None = None
    authenticity_status: str = "unchecked"
    parsing_status: str = "collected"
    extraction_warnings: list[str] = Field(default_factory=list)
    review_status: Literal["unreviewed", "reviewed", "rejected"] = "unreviewed"
    last_verification_date: date | None = None
    reviewer_notes: str | None = None
    provenance_notes: str | None = None
    redistribution_permitted: bool = False

    @model_validator(mode="after")
    def boundaries(self):
        if self.namespace not in ("official", "synthetic") and not self.namespace.startswith("private:"):
            raise ValueError("Namespace must be official, synthetic or private:<session>")
        if self.effective_until and self.effective_date and self.effective_until < self.effective_date:
            raise ValueError("Invalid effective date range")
        return self


class Chunk(BaseModel):
    chunk_id: str
    version_id: str
    source_checksum: str
    document_id: str
    domain: Domain
    jurisdiction: str
    namespace: str
    ordinal: int
    kind: Literal["parent", "child"]
    parent_id: str | None = None
    page_start: int | None = None  # Physical PDF pages are 1-based.
    page_end: int | None = None
    printed_page: str | None = None  # Never inferred from physical pagination.
    locator: str | None = None
    content_role: str = 'text'
    text: str


class Filters(BaseModel):
    namespace: str = "official"
    domain: Domain | None = None
    jurisdiction: str | None = None
    state: str | None = None
    as_of: date | None = None
    review_mode: Literal["demo", "reviewed", "synthetic", "private"] = "demo"
    version_ids: list[str] = Field(default_factory=list)
    include_superseded: bool = False


class Hit(BaseModel):
    chunk: Chunk
    source: Source
    score: float
    ranks: dict[str, int] = Field(default_factory=dict)
    context: list[Chunk] = Field(default_factory=list)


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    citation_ids: list[str] = Field(min_length=1, max_length=10)
    quotes: dict[str, str] = Field(default_factory=dict)


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["supported", "needs clarification", "insufficient evidence", "conflict"]
    claims: list[Claim] = Field(default_factory=list, max_length=10)
    uncertainties: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)


class Answer(BaseModel):
    status: str
    text: str
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Hit] = Field(default_factory=list)
    scope: dict = Field(default_factory=dict)
    uncertainties: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    timings: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    mode: str = "extractive"

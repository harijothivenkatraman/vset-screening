"""Pydantic schemas for the Company Discovery presentation layer."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateItemSchema(BaseModel):
    url: str
    title: str
    snippet: str
    domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    search_query: str
    entity_name: str


class ResolveCandidatesRequest(BaseModel):
    company_name: str = Field(min_length=1)
    founder_names: list[str] = Field(min_length=1)
    website_override: str | None = None
    company_linkedin_override: str | None = None
    founder_linkedin_overrides: dict[str, str] | None = None


class ResolveCandidatesResponse(BaseModel):
    candidates: dict[str, list[CandidateItemSchema]]
    search_unavailable: bool
    error_message: str | None = None


class ManualEvidenceItemSchema(BaseModel):
    text: str | None = None
    pdf_base64: str | None = None
    pdf_filename: str | None = None


class StartDiscoveryJobRequest(BaseModel):
    company_name: str = Field(min_length=1)
    founder_names: list[str] = Field(min_length=1)
    confirmed_urls: dict[str, str] = Field(default_factory=dict)
    search_snippets: dict[str, str] = Field(default_factory=dict)
    manual_evidence: dict[str, ManualEvidenceItemSchema] = Field(default_factory=dict)
    llm_model: str | None = None


class StartDiscoveryJobResponse(BaseModel):
    job_id: str
    state: str
    message: str


class SourceDiagnosticSchema(BaseModel):
    url: str
    outcome: str
    bytes_fetched: int = 0
    fields_extracted: list[str] = Field(default_factory=list)
    error_details: str | None = None


class DiscoveryJobStatusResponse(BaseModel):
    job_id: str
    company_name: str
    state: str
    stage: str
    progress: float
    warnings: list[str]
    result_slug: str | None = None
    error_message: str | None = None
    diagnostics: list[SourceDiagnosticSchema] = Field(default_factory=list)


class DiscoveryHealthResponse(BaseModel):
    status: str
    discovery_enabled: bool
    llm_reachable: bool
    model_available: bool = True
    llm_model: str
    installed_models: list[str] = Field(default_factory=list)
    search_providers: list[str]
    free_disk_gb: float

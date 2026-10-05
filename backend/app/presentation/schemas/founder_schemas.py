"""Pydantic schemas for the Founder Profiles presentation layer."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ExperienceItemSchema(BaseModel):
    title: str = ""
    company: str = ""
    start: str = ""
    end: str = ""
    duration: str = ""
    description: str = ""
    is_current: bool = False
    location: str = ""


class EducationItemSchema(BaseModel):
    school: str = ""
    degree: str = ""
    field: str = ""
    start_year: str = ""
    end_year: str = ""


class RetrievalSchema(BaseModel):
    status: str = "user_provided"
    source_type: str = "user_supplied"
    retrieved_at: str = ""
    source_id: str | None = None
    sections_available: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    verification_reason: str | None = None
    source_label: str | None = None


class FounderProfileResponse(BaseModel):
    id: str
    slug: str
    founder_name: str
    company_name: str | None = None
    headline: str | None = None
    location: str | None = None
    about: str | None = None
    screening_assessment: str | None = None
    linkedin_url: str | None = None
    experience_timeline: list[ExperienceItemSchema] = Field(default_factory=list)
    education: list[EducationItemSchema] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    retrieval: RetrievalSchema
    identity_status: str
    notes: str | None = None
    has_previous_version: bool = False
    created_at: str
    updated_at: str

    model_config = {"extra": "allow"}


class FounderProfileListResponse(BaseModel):
    items: list[FounderProfileResponse]
    total: int
    limit: int
    offset: int


class AddFounderProfileRequest(BaseModel):
    founder_name: str
    company_name: str | None = None
    evidence_text: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    allow_duplicate: bool = False


class UpdateFounderProfileRequest(BaseModel):
    evidence_text: str | None = None
    linkedin_url: str | None = None
    screening_assessment: str | None = None
    notes: str | None = None


class TryPublicFetchRequest(BaseModel):
    founder_name: str
    linkedin_url: str
    company_name: str | None = None


class SavePendingProfileRequest(BaseModel):
    founder_name: str
    company_name: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    verification_reason: str | None = None
    allow_duplicate: bool = False


class TryPublicFetchResponse(BaseModel):
    success: bool
    message: str
    status: str
    profile: FounderProfileResponse | None = None
    verification_reason: str | None = None


class DuplicateConflictResponse(BaseModel):
    detail: str
    existing_id: str
    existing_slug: str


class AutoDiscoverRequest(BaseModel):
    founder_name: str
    company_name: str | None = None
    profile_url: str | None = None
    company_website: str | None = None


class AutoDiscoverResponse(BaseModel):
    outcome: str
    candidate: FounderProfileResponse | None = None
    persisted: bool = False
    message: str
    discovered_url: str | None = None


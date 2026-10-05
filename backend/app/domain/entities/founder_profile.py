"""Domain entities for standalone founder profile management.

Defines the FounderProfile aggregate root, value objects for career timelines,
education records, retrieval diagnostics, and version snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

# Identity status enum:
# - "verified": Proven by domain links, website proximity, or reference report
# - "user_asserted": Sourced from user-provided text or uploaded PDF
# - "likely_match": Name and company mentioned, but lacks domain proof (requires confirmation)
# - "unverified": Candidate not corroborated or rejected
IdentityStatusType = Literal["verified", "user_asserted", "likely_match", "unverified"]

# Retrieval status enum:
RetrievalStatusType = Literal[
    "retrieved",
    "user_provided",
    "reference_screen",
    "identity_unverified",
    "blocked_by_bot_protection",
    "not_found",
    "pending_evidence",
]


@dataclass(frozen=True)
class ExperienceTimelineItem:
    """A single employment or leadership role in a founder's career history."""
    title: str
    company: str
    start: str = ""
    end: str = ""
    duration: str = ""
    description: str = ""
    is_current: bool = False
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "description": self.description,
            "is_current": self.is_current,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperienceTimelineItem:
        return cls(
            title=str(data.get("title") or ""),
            company=str(data.get("company") or ""),
            start=str(data.get("start") or ""),
            end=str(data.get("end") or ""),
            duration=str(data.get("duration") or ""),
            description=str(data.get("description") or ""),
            is_current=bool(data.get("is_current", False)),
            location=str(data.get("location") or ""),
        )


@dataclass(frozen=True)
class EducationItem:
    """An academic institution, degree, or qualification."""
    school: str
    degree: str = ""
    field: str = ""
    start_year: str = ""
    end_year: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "school": self.school,
            "degree": self.degree,
            "field": self.field,
            "start_year": self.start_year,
            "end_year": self.end_year,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EducationItem:
        return cls(
            school=str(data.get("school") or data.get("institution") or ""),
            degree=str(data.get("degree") or ""),
            field=str(data.get("field") or ""),
            start_year=str(data.get("start_year") or data.get("year") or ""),
            end_year=str(data.get("end_year") or ""),
        )


@dataclass(frozen=True)
class RetrievalPayload:
    """Telemetry and provenance metadata describing how profile data was acquired."""
    status: RetrievalStatusType = "user_provided"
    source_type: str = "user_supplied"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_id: str | None = None
    sections_available: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    verification_reason: str | None = None
    source_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at,
            "source_id": self.source_id,
            "sections_available": list(self.sections_available),
            "warnings": list(self.warnings),
            "verification_reason": self.verification_reason,
            "source_label": self.source_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievalPayload:
        raw_status = data.get("status", "user_provided")
        typed_status: RetrievalStatusType = raw_status if raw_status in (
            "retrieved", "user_provided", "reference_screen", "identity_unverified",
            "blocked_by_bot_protection", "not_found", "pending_evidence"
        ) else "user_provided"
        return cls(
            status=typed_status,
            source_type=str(data.get("source_type") or "user_supplied"),
            retrieved_at=str(data.get("retrieved_at") or datetime.now(timezone.utc).isoformat()),
            source_id=data.get("source_id"),
            sections_available=list(data.get("sections_available") or []),
            warnings=list(data.get("warnings") or []),
            verification_reason=data.get("verification_reason"),
            source_label=data.get("source_label"),
        )


@dataclass
class FounderProfile:
    """Aggregate root representing a founder's verified or user-asserted profile."""
    id: UUID
    slug: str
    founder_name: str
    company_name: str | None = None
    headline: str | None = None
    location: str | None = None
    about: str | None = None
    linkedin_url: str | None = None
    experience_timeline: list[ExperienceTimelineItem] = field(default_factory=list)
    education: list[EducationItem] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    retrieval: RetrievalPayload = field(default_factory=RetrievalPayload)
    identity_status: IdentityStatusType = "user_asserted"
    notes: str | None = None
    previous_version: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def create_version_snapshot(self) -> dict[str, Any]:
        """Create a restorable snapshot of the current state before an explicit user update."""
        return {
            "headline": self.headline,
            "location": self.location,
            "about": self.about,
            "linkedin_url": self.linkedin_url,
            "experience_timeline": [exp.to_dict() for exp in self.experience_timeline],
            "education": [edu.to_dict() for edu in self.education],
            "skills": list(self.skills),
            "certifications": list(self.certifications),
            "languages": list(self.languages),
            "retrieval": self.retrieval.to_dict(),
            "identity_status": self.identity_status,
            "notes": self.notes,
            "updated_at": self.updated_at.isoformat(),
        }

    def restore_from_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Restore profile fields from a previous snapshot."""
        self.headline = snapshot.get("headline")
        self.location = snapshot.get("location")
        self.about = snapshot.get("about")
        self.linkedin_url = snapshot.get("linkedin_url")
        self.experience_timeline = [
            ExperienceTimelineItem.from_dict(item)
            for item in snapshot.get("experience_timeline", [])
        ]
        self.education = [
            EducationItem.from_dict(item)
            for item in snapshot.get("education", [])
        ]
        self.skills = list(snapshot.get("skills", []))
        self.certifications = list(snapshot.get("certifications", []))
        self.languages = list(snapshot.get("languages", []))
        if "retrieval" in snapshot and isinstance(snapshot["retrieval"], dict):
            self.retrieval = RetrievalPayload.from_dict(snapshot["retrieval"])
        self.identity_status = snapshot.get("identity_status", "user_asserted")
        self.notes = snapshot.get("notes")
        self.updated_at = datetime.now(timezone.utc)
        # Clear previous_version once restored so it cannot be double-restored
        self.previous_version = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "founder_name": self.founder_name,
            "company_name": self.company_name,
            "headline": self.headline,
            "location": self.location,
            "about": self.about,
            "linkedin_url": self.linkedin_url,
            "experience_timeline": [exp.to_dict() for exp in self.experience_timeline],
            "education": [edu.to_dict() for edu in self.education],
            "skills": list(self.skills),
            "certifications": list(self.certifications),
            "languages": list(self.languages),
            "retrieval": self.retrieval.to_dict(),
            "identity_status": self.identity_status,
            "notes": self.notes,
            "has_previous_version": self.previous_version is not None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

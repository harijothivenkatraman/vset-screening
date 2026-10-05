"""SQLAlchemy models for standalone Founder Profiles."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FounderProfileModel(Base):
    __tablename__ = "founder_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    founder_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    screening_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    certifications: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    retrieval: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    identity_status: Mapped[str] = mapped_column(String(50), nullable=False, default="user_asserted", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_version: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

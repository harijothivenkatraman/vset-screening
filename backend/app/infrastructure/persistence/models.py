import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CompanyModel(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    reports: Mapped[list["ReportModel"]] = relationship(
        "ReportModel", back_populates="company", cascade="all, delete-orphan"
    )


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_screen_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    report_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    audience: Mapped[str] = mapped_column(String(50), nullable=False, default="FOUNDER")
    audience_label: Mapped[str] = mapped_column(String(100), nullable=False, default="Founder Screen")
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="V1")
    canonical_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    research_cutoff: Mapped[str | None] = mapped_column(String(50), nullable=True)
    as_of_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cover: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ribbon: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    presentation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    report_basis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    concerns_conflicts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company: Mapped["CompanyModel"] = relationship("CompanyModel", back_populates="reports")
    sections: Mapped[list["SectionModel"]] = relationship(
        "SectionModel", back_populates="report", cascade="all, delete-orphan", order_by="SectionModel.position"
    )
    action_items: Mapped[list["ActionItemModel"]] = relationship(
        "ActionItemModel", back_populates="report", cascade="all, delete-orphan", order_by="ActionItemModel.position"
    )
    sources: Mapped[list["SourceModel"]] = relationship(
        "SourceModel", back_populates="report", cascade="all, delete-orphan", order_by="SourceModel.position"
    )
    raw_snapshot: Mapped["RawSnapshotModel | None"] = relationship(
        "RawSnapshotModel", back_populates="report", uselist=False, cascade="all, delete-orphan"
    )


class SectionModel(Base):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    ribbon: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    blocks: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped["ReportModel"] = relationship("ReportModel", back_populates="sections")


class ActionItemModel(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    where: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    semantic_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped["ReportModel"] = relationship("ReportModel", back_populates="action_items")


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ownership_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped["ReportModel"] = relationship("ReportModel", back_populates="sources")


class RawSnapshotModel(Base):
    __tablename__ = "raw_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped["ReportModel"] = relationship("ReportModel", back_populates="raw_snapshot")

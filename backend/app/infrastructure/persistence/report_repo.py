from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.report_repository import ReportRepository
from app.domain.entities.report import Report
from app.infrastructure.persistence.models import RawSnapshotModel, ReportModel


def _model_to_entity(model: ReportModel) -> Report:
    return Report(
        id=model.id,
        company_id=model.company_id,
        canonical_screen_id=model.canonical_screen_id,
        report_id=model.report_id,
        final_fingerprint=model.final_fingerprint,
        audience=model.audience,
        audience_label=model.audience_label,
        version=model.version,
        canonical_version=model.canonical_version,
        schema_version=model.schema_version,
        research_cutoff=model.research_cutoff,
        as_of_date=model.as_of_date,
        generated_at=model.generated_at,
        cover=model.cover,
        ribbon=model.ribbon,
        presentation=model.presentation,
        report_basis=model.report_basis,
        concerns_conflicts=model.concerns_conflicts,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


import re

def sanitize_audit_snapshot(obj: Any) -> Any:
    """Recursively scrub raw profile text, contact info (emails, phones), and photo URLs from audit snapshots."""
    email_re = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
    phone_re = re.compile(
        r"(?<![\w$€£₹])\+\d{1,4}[-.\s]?(?:\(?\d{1,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}(?:[-.\s]?\d{1,4})?(?![\w])"
        r"|(?<![\w$€£₹])\(\d{2,4}\)[-.\s]?\d{3,4}[-.\s]?\d{3,5}(?![\w])"
        r"|(?<![\w$€£₹])0[6-9]\d{4}[-.\s]?\d{5}(?![\w])"
        r"|(?<![\w$€£₹])0[6-9]\d{9}(?![\w])"
        r"|(?<![\w$€£₹])\b[6-9]\d{4}[-.\s]\d{5}(?![\w])"
        r"|(?<![\w$€£₹])\b[6-9]\d{9}\b(?![\w])"
        r"|(?<![\w$€£₹])(?!(?:19|20)\d{2}[-.\/](?:0?[1-9]|1[0-2]))\b\d{3}[-.]\d{3}[-.]\d{4}(?![\w])"
    )

    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if k_lower in ("email", "phone", "mobile", "contact", "contact_info", "avatar_url", "photo_url", "raw_profile_text", "raw_text", "pdf_base64"):
                continue
            cleaned[k] = sanitize_audit_snapshot(v)
        return cleaned
    elif isinstance(obj, list):
        return [sanitize_audit_snapshot(item) for item in obj]
    elif isinstance(obj, str):
        s = email_re.sub("", obj)
        s = phone_re.sub("", s)
        return s.strip()
    return obj


class SqlAlchemyReportRepository(ReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, report_id: UUID) -> Report | None:
        stmt = select(ReportModel).where(ReportModel.id == report_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def find_by_company_id(self, company_id: UUID) -> Report | None:
        stmt = (
            select(ReportModel)
            .where(ReportModel.company_id == company_id)
            .order_by(ReportModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return _model_to_entity(model) if model else None

    async def find_by_canonical_screen_id(self, canonical_screen_id: str) -> Report | None:
        stmt = select(ReportModel).where(ReportModel.canonical_screen_id == canonical_screen_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def save(self, report: Report) -> Report:
        model = await self._session.get(ReportModel, report.id)
        if model is None:
            model = ReportModel(
                id=report.id,
                company_id=report.company_id,
                canonical_screen_id=report.canonical_screen_id,
                report_id=report.report_id,
                final_fingerprint=report.final_fingerprint,
                audience=report.audience,
                audience_label=report.audience_label,
                version=report.version,
                canonical_version=report.canonical_version,
                schema_version=report.schema_version,
                research_cutoff=report.research_cutoff,
                as_of_date=report.as_of_date,
                generated_at=report.generated_at,
                cover=report.cover,
                ribbon=report.ribbon,
                presentation=report.presentation,
                report_basis=report.report_basis,
                concerns_conflicts=report.concerns_conflicts,
                created_at=report.created_at,
                updated_at=report.updated_at,
            )
            self._session.add(model)
        else:
            model.final_fingerprint = report.final_fingerprint
            model.audience = report.audience
            model.audience_label = report.audience_label
            model.version = report.version
            model.canonical_version = report.canonical_version
            model.schema_version = report.schema_version
            model.research_cutoff = report.research_cutoff
            model.as_of_date = report.as_of_date
            model.generated_at = report.generated_at
            model.cover = report.cover
            model.ribbon = report.ribbon
            model.presentation = report.presentation
            model.report_basis = report.report_basis
            model.concerns_conflicts = report.concerns_conflicts
            model.updated_at = report.updated_at
        await self._session.flush()
        return _model_to_entity(model)

    async def save_raw_snapshot(self, report_id: UUID, raw_json: dict[str, Any], content_fingerprint: str) -> None:
        clean_snapshot = sanitize_audit_snapshot(raw_json)
        stmt = select(RawSnapshotModel).where(RawSnapshotModel.report_id == report_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            model = RawSnapshotModel(
                id=uuid4(),
                report_id=report_id,
                raw_json=clean_snapshot,
                content_fingerprint=content_fingerprint,
            )
            self._session.add(model)
        else:
            model.raw_json = clean_snapshot
            model.content_fingerprint = content_fingerprint
        await self._session.flush()

    async def get_raw_snapshot(self, report_id: UUID) -> dict[str, Any] | None:
        stmt = select(RawSnapshotModel).where(RawSnapshotModel.report_id == report_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.raw_json if model else None

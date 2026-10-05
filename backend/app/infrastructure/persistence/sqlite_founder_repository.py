"""SQLAlchemy / SQLite implementation of the FounderProfileRepository port."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import (
    EducationItem,
    ExperienceTimelineItem,
    FounderProfile,
    RetrievalPayload,
)
from app.infrastructure.persistence.models import FounderProfileModel


def _model_to_entity(model: FounderProfileModel) -> FounderProfile:
    return FounderProfile(
        id=model.id,
        slug=model.slug,
        founder_name=model.founder_name,
        company_name=model.company_name,
        headline=model.headline,
        location=model.location,
        about=model.about,
        linkedin_url=model.linkedin_url,
        experience_timeline=[
            ExperienceTimelineItem.from_dict(item)
            for item in (model.experience_timeline or [])
        ],
        education=[
            EducationItem.from_dict(item)
            for item in (model.education or [])
        ],
        skills=list(model.skills or []),
        certifications=list(model.certifications or []),
        languages=list(model.languages or []),
        retrieval=RetrievalPayload.from_dict(model.retrieval or {}),
        identity_status=model.identity_status,  # type: ignore[arg-type]
        notes=model.notes,
        previous_version=model.previous_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqliteFounderProfileRepository(FounderProfileRepository):
    """Repository implementation using SQLAlchemy AsyncSession targeting SQLite (or Postgres)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, profile: FounderProfile) -> FounderProfile:
        model = await self._session.get(FounderProfileModel, profile.id)
        if model is None:
            model = FounderProfileModel(
                id=profile.id,
                slug=profile.slug,
                founder_name=profile.founder_name,
                company_name=profile.company_name,
                headline=profile.headline,
                location=profile.location,
                about=profile.about,
                linkedin_url=profile.linkedin_url,
                experience_timeline=[exp.to_dict() for exp in profile.experience_timeline],
                education=[edu.to_dict() for edu in profile.education],
                skills=profile.skills,
                certifications=profile.certifications,
                languages=profile.languages,
                retrieval=profile.retrieval.to_dict(),
                identity_status=profile.identity_status,
                notes=profile.notes,
                previous_version=profile.previous_version,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            self._session.add(model)
        else:
            model.slug = profile.slug
            model.founder_name = profile.founder_name
            model.company_name = profile.company_name
            model.headline = profile.headline
            model.location = profile.location
            model.about = profile.about
            model.linkedin_url = profile.linkedin_url
            model.experience_timeline = [exp.to_dict() for exp in profile.experience_timeline]
            model.education = [edu.to_dict() for edu in profile.education]
            model.skills = profile.skills
            model.certifications = profile.certifications
            model.languages = profile.languages
            model.retrieval = profile.retrieval.to_dict()
            model.identity_status = profile.identity_status
            model.notes = profile.notes
            model.previous_version = profile.previous_version
            model.updated_at = profile.updated_at

        await self._session.flush()
        await self._session.commit()
        return _model_to_entity(model)

    async def find_by_id(self, profile_id: UUID) -> FounderProfile | None:
        stmt = select(FounderProfileModel).where(FounderProfileModel.id == profile_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def find_by_slug(self, slug: str) -> FounderProfile | None:
        stmt = select(FounderProfileModel).where(FounderProfileModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def find_by_name_and_company(
        self, founder_name: str, company_name: str | None
    ) -> FounderProfile | None:
        stmt = select(FounderProfileModel).where(
            func.lower(FounderProfileModel.founder_name) == founder_name.strip().lower()
        )
        if company_name and company_name.strip():
            stmt = stmt.where(
                func.lower(FounderProfileModel.company_name) == company_name.strip().lower()
            )
        else:
            stmt = stmt.where(
                or_(
                    FounderProfileModel.company_name.is_(None),
                    FounderProfileModel.company_name == "",
                )
            )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    def _build_filter_conditions(
        self, search: str | None = None, status: str | None = None
    ) -> list[Any]:
        conditions: list[Any] = []
        if search and search.strip():
            pattern = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(FounderProfileModel.founder_name).like(pattern),
                    func.lower(FounderProfileModel.company_name).like(pattern),
                    func.lower(FounderProfileModel.headline).like(pattern),
                )
            )
        if status and status.strip():
            conditions.append(FounderProfileModel.identity_status == status.strip())
        return conditions

    async def list_all(
        self,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FounderProfile]:
        stmt = select(FounderProfileModel)
        conditions = self._build_filter_conditions(search=search, status=status)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(FounderProfileModel.updated_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        search: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count(FounderProfileModel.id))
        conditions = self._build_filter_conditions(search=search, status=status)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self._session.execute(stmt)
        val = result.scalar_one()
        return int(val or 0)

    async def delete(self, profile_id: UUID) -> bool:
        stmt = select(FounderProfileModel).where(FounderProfileModel.id == profile_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

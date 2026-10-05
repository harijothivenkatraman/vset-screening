from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.company_repository import CompanyRepository
from app.domain.entities.company import Company
from app.infrastructure.persistence.models import CompanyModel


def _model_to_entity(model: CompanyModel) -> Company:
    return Company(
        id=model.id,
        slug=model.slug,
        name=model.name,
        website=model.website,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyCompanyRepository(CompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_all(self) -> list[Company]:
        stmt = select(CompanyModel).order_by(CompanyModel.name)
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def find_by_id(self, company_id: UUID) -> Company | None:
        stmt = select(CompanyModel).where(CompanyModel.id == company_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def find_by_slug(self, slug: str) -> Company | None:
        stmt = select(CompanyModel).where(CompanyModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def find_by_name(self, name: str) -> Company | None:
        stmt = select(CompanyModel).where(CompanyModel.name == name)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def save(self, company: Company) -> Company:
        model = await self._session.get(CompanyModel, company.id)
        if model is None:
            model = CompanyModel(
                id=company.id,
                slug=company.slug,
                name=company.name,
                website=company.website,
                created_at=company.created_at,
                updated_at=company.updated_at,
            )
            self._session.add(model)
        else:
            model.slug = company.slug
            model.name = company.name
            model.website = company.website
            model.updated_at = company.updated_at
        await self._session.flush()
        return _model_to_entity(model)

    async def delete_by_slug(self, slug: str) -> bool:
        stmt = select(CompanyModel).where(CompanyModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

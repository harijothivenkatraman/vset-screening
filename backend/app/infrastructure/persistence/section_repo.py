from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.section_repository import SectionRepository
from app.domain.entities.section import Section
from app.infrastructure.persistence.models import SectionModel


def _model_to_entity(model: SectionModel) -> Section:
    return Section(
        id=model.id,
        report_id=model.report_id,
        key=model.key,
        title=model.title,
        position=model.position,
        ribbon=model.ribbon,
        blocks=model.blocks,
        created_at=model.created_at,
    )


class SqlAlchemySectionRepository(SectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_report_id(self, report_id: UUID) -> list[Section]:
        stmt = (
            select(SectionModel)
            .where(SectionModel.report_id == report_id)
            .order_by(SectionModel.position)
        )
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def find_by_report_id_and_key(self, report_id: UUID, key: str) -> Section | None:
        stmt = (
            select(SectionModel)
            .where(SectionModel.report_id == report_id, SectionModel.key == key)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_entity(model) if model else None

    async def save_many(self, sections: list[Section]) -> list[Section]:
        models = [
            SectionModel(
                id=s.id,
                report_id=s.report_id,
                key=s.key,
                title=s.title,
                position=s.position,
                ribbon=s.ribbon,
                blocks=s.blocks,
                created_at=s.created_at,
            )
            for s in sections
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_model_to_entity(m) for m in models]

    async def delete_by_report_id(self, report_id: UUID) -> None:
        stmt = delete(SectionModel).where(SectionModel.report_id == report_id)
        await self._session.execute(stmt)
        await self._session.flush()

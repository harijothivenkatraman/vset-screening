from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.source_repository import SourceRepository
from app.domain.entities.source import Source
from app.infrastructure.persistence.models import SourceModel


def _model_to_entity(model: SourceModel) -> Source:
    return Source(
        id=model.id,
        report_id=model.report_id,
        source_id=model.source_id,
        title=model.title,
        publisher=model.publisher,
        published_date=model.published_date,
        display_url=model.display_url,
        canonical_url=model.canonical_url,
        source_type=model.source_type,
        ownership_class=model.ownership_class,
        position=model.position,
        created_at=model.created_at,
    )


class SqlAlchemySourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_report_id(self, report_id: UUID) -> list[Source]:
        stmt = (
            select(SourceModel)
            .where(SourceModel.report_id == report_id)
            .order_by(SourceModel.position)
        )
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def save_many(self, sources: list[Source]) -> list[Source]:
        models = [
            SourceModel(
                id=s.id,
                report_id=s.report_id,
                source_id=s.source_id,
                title=s.title,
                publisher=s.publisher,
                published_date=s.published_date,
                display_url=s.display_url,
                canonical_url=s.canonical_url,
                source_type=s.source_type,
                ownership_class=s.ownership_class,
                position=s.position,
                created_at=s.created_at,
            )
            for s in sources
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_model_to_entity(m) for m in models]

    async def delete_by_report_id(self, report_id: UUID) -> None:
        stmt = delete(SourceModel).where(SourceModel.report_id == report_id)
        await self._session.execute(stmt)
        await self._session.flush()

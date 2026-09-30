from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.action_item_repository import ActionItemRepository
from app.domain.entities.action_item import ActionItem
from app.infrastructure.persistence.models import ActionItemModel


def _model_to_entity(model: ActionItemModel) -> ActionItem:
    return ActionItem(
        id=model.id,
        report_id=model.report_id,
        action_id=model.action_id,
        kind=model.kind,
        where=model.where,
        domain=model.domain,
        topic=model.topic,
        group_name=model.group_name,
        text=model.text,
        why=model.why,
        key=model.key,
        semantic_key=model.semantic_key,
        priority_level=model.priority_level,
        position=model.position,
        created_at=model.created_at,
    )


class SqlAlchemyActionItemRepository(ActionItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_report_id(self, report_id: UUID) -> list[ActionItem]:
        stmt = (
            select(ActionItemModel)
            .where(ActionItemModel.report_id == report_id)
            .order_by(ActionItemModel.position)
        )
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def find_by_report_id_and_kind(self, report_id: UUID, kind: str) -> list[ActionItem]:
        stmt = (
            select(ActionItemModel)
            .where(ActionItemModel.report_id == report_id, ActionItemModel.kind == kind)
            .order_by(ActionItemModel.position)
        )
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def find_by_report_id_and_where(self, report_id: UUID, where: str) -> list[ActionItem]:
        stmt = (
            select(ActionItemModel)
            .where(ActionItemModel.report_id == report_id, ActionItemModel.where == where)
            .order_by(ActionItemModel.position)
        )
        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]

    async def save_many(self, action_items: list[ActionItem]) -> list[ActionItem]:
        models = [
            ActionItemModel(
                id=a.id,
                report_id=a.report_id,
                action_id=a.action_id,
                kind=a.kind,
                where=a.where,
                domain=a.domain,
                topic=a.topic,
                group_name=a.group_name,
                text=a.text,
                why=a.why,
                key=a.key,
                semantic_key=a.semantic_key,
                priority_level=a.priority_level,
                position=a.position,
                created_at=a.created_at,
            )
            for a in action_items
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_model_to_entity(m) for m in models]

    async def delete_by_report_id(self, report_id: UUID) -> None:
        stmt = delete(ActionItemModel).where(ActionItemModel.report_id == report_id)
        await self._session.execute(stmt)
        await self._session.flush()

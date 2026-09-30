from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.action_item import ActionItem


class ActionItemRepository(ABC):
    @abstractmethod
    async def find_by_report_id(self, report_id: UUID) -> list[ActionItem]:
        pass

    @abstractmethod
    async def find_by_report_id_and_kind(self, report_id: UUID, kind: str) -> list[ActionItem]:
        pass

    @abstractmethod
    async def find_by_report_id_and_where(self, report_id: UUID, where: str) -> list[ActionItem]:
        pass

    @abstractmethod
    async def save_many(self, action_items: list[ActionItem]) -> list[ActionItem]:
        pass

    @abstractmethod
    async def delete_by_report_id(self, report_id: UUID) -> None:
        pass

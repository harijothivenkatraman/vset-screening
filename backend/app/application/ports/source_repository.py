from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.source import Source


class SourceRepository(ABC):
    @abstractmethod
    async def find_by_report_id(self, report_id: UUID) -> list[Source]:
        pass

    @abstractmethod
    async def save_many(self, sources: list[Source]) -> list[Source]:
        pass

    @abstractmethod
    async def delete_by_report_id(self, report_id: UUID) -> None:
        pass

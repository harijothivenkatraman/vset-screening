from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.section import Section


class SectionRepository(ABC):
    @abstractmethod
    async def find_by_report_id(self, report_id: UUID) -> list[Section]:
        pass

    @abstractmethod
    async def find_by_report_id_and_key(self, report_id: UUID, key: str) -> Section | None:
        pass

    @abstractmethod
    async def save_many(self, sections: list[Section]) -> list[Section]:
        pass

    @abstractmethod
    async def delete_by_report_id(self, report_id: UUID) -> None:
        pass

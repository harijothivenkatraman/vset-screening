from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.domain.entities.report import Report


class ReportRepository(ABC):
    @abstractmethod
    async def find_by_id(self, report_id: UUID) -> Report | None:
        pass

    @abstractmethod
    async def find_by_company_id(self, company_id: UUID) -> Report | None:
        pass

    @abstractmethod
    async def find_by_canonical_screen_id(self, canonical_screen_id: str) -> Report | None:
        pass

    @abstractmethod
    async def save(self, report: Report) -> Report:
        pass

    @abstractmethod
    async def save_raw_snapshot(self, report_id: UUID, raw_json: dict[str, Any], content_fingerprint: str) -> None:
        pass

    @abstractmethod
    async def get_raw_snapshot(self, report_id: UUID) -> dict[str, Any] | None:
        pass

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.company import Company


class CompanyRepository(ABC):
    @abstractmethod
    async def find_all(self) -> list[Company]:
        pass

    @abstractmethod
    async def find_by_id(self, company_id: UUID) -> Company | None:
        pass

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Company | None:
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Company | None:
        pass

    @abstractmethod
    async def save(self, company: Company) -> Company:
        pass

    @abstractmethod
    async def delete_by_slug(self, slug: str) -> bool:
        pass

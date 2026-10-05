"""Application service to delete a company and cascade-delete its reports, sections, sources, and snapshots."""
from __future__ import annotations

from app.application.ports.company_repository import CompanyRepository


class DeleteCompanyService:
    def __init__(self, company_repo: CompanyRepository) -> None:
        self._company_repo = company_repo

    async def execute(self, slug: str) -> bool:
        """Delete company by slug with full cascade to child entities."""
        return await self._company_repo.delete_by_slug(slug)

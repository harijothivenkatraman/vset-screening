from typing import Any

from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.section_repository import SectionRepository


class SectionNavItem:
    def __init__(self, key: str, title: str, position: int) -> None:
        self.key = key
        self.title = title
        self.position = position

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "position": self.position,
        }


class GetSectionNavService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
        section_repo: SectionRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo
        self._section_repo = section_repo

    async def execute(self, slug: str) -> list[SectionNavItem] | None:
        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            return None

        report = await self._report_repo.find_by_company_id(company.id)
        if report is None:
            return None

        sections = await self._section_repo.find_by_report_id(report.id)
        return [
            SectionNavItem(key=s.key, title=s.title, position=s.position)
            for s in sections
        ]

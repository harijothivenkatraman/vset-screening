from typing import Any

from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository


class ReportHeaderData:
    def __init__(
        self,
        slug: str,
        name: str,
        cover: dict[str, Any],
        ribbon: list[Any],
        audience_label: str,
        as_of_date: str | None,
        generated_at: str | None,
        presentation: dict[str, Any],
    ) -> None:
        self.slug = slug
        self.name = name
        self.cover = cover
        self.ribbon = ribbon
        self.audience_label = audience_label
        self.as_of_date = as_of_date
        self.generated_at = generated_at
        self.presentation = presentation

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "cover": self.cover,
            "ribbon": self.ribbon,
            "audienceLabel": self.audience_label,
            "asOfDate": self.as_of_date,
            "generatedAt": self.generated_at,
            "presentation": self.presentation,
        }


class GetReportHeaderService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo

    async def execute(self, slug: str) -> ReportHeaderData | None:
        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            return None

        report = await self._report_repo.find_by_company_id(company.id)
        if report is None:
            return None

        return ReportHeaderData(
            slug=company.slug,
            name=company.name,
            cover=report.cover,
            ribbon=report.ribbon,
            audience_label=report.audience_label,
            as_of_date=report.as_of_date,
            generated_at=report.generated_at.isoformat() if report.generated_at else None,
            presentation=report.presentation,
        )

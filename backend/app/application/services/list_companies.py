from typing import Any

from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository


class CompanyListItem:
    def __init__(
        self,
        slug: str,
        name: str,
        website: str | None,
        audience_label: str,
        stage: str | None,
        sector: str | None,
    ) -> None:
        self.slug = slug
        self.name = name
        self.website = website
        self.audience_label = audience_label
        self.stage = stage
        self.sector = sector

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "website": self.website,
            "audienceLabel": self.audience_label,
            "stage": self.stage,
            "sector": self.sector,
        }


class ListCompaniesService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo

    async def execute(self) -> list[CompanyListItem]:
        companies = await self._company_repo.find_all()
        results: list[CompanyListItem] = []

        for c in companies:
            report = await self._report_repo.find_by_company_id(c.id)
            audience_label = report.audience_label if report else "Founder Screen"
            stage = None
            sector = None
            if report and report.ribbon:
                for item in report.ribbon:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        label, val = item
                        if label.lower() == "stage":
                            stage = val
                        elif label.lower() == "sector":
                            sector = val

            results.append(
                CompanyListItem(
                    slug=c.slug,
                    name=c.name,
                    website=c.website,
                    audience_label=audience_label,
                    stage=stage,
                    sector=sector,
                )
            )

        return results

from typing import Any

from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.source_repository import SourceRepository


class SourcesData:
    def __init__(
        self,
        about_text: str,
        limitations: list[str],
        research_window: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> None:
        self.about_text = about_text
        self.limitations = limitations
        self.research_window = research_window
        self.sources = sources

    def to_dict(self) -> dict[str, Any]:
        return {
            "aboutText": self.about_text,
            "limitations": self.limitations,
            "researchWindow": self.research_window,
            "sources": self.sources,
        }


class GetSourcesService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
        source_repo: SourceRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo
        self._source_repo = source_repo

    async def execute(self, slug: str) -> SourcesData | None:
        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            return None

        report = await self._report_repo.find_by_company_id(company.id)
        if report is None:
            return None

        basis = report.report_basis or {}
        pres = report.presentation or {}

        about_text = (
            pres.get("about_screen_audience_text")
            or basis.get("scope_statement")
            or "Independent public-source assessment."
        )
        limitations = basis.get("limitations", [])
        research_window = basis.get("research_window", {})

        sources_entities = await self._source_repo.find_by_report_id(report.id)
        sources_list = [
            {
                "sourceId": s.source_id,
                "position": s.position + 1,  # 1-indexed for display S1, S2...
                "title": s.title,
                "publisher": s.publisher,
                "publishedDate": s.published_date,
                "displayUrl": s.display_url,
                "canonicalUrl": s.canonical_url,
            }
            for s in sources_entities
        ]

        return SourcesData(
            about_text=about_text,
            limitations=limitations,
            research_window=research_window,
            sources=sources_list,
        )

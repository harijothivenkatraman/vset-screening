from typing import Any

from app.application.ports.action_item_repository import ActionItemRepository
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.section_repository import SectionRepository


class SectionDetailData:
    def __init__(
        self,
        key: str,
        title: str,
        position: int,
        ribbon: list[Any],
        blocks: list[Any],
        information_to_prepare: list[dict[str, Any]],
    ) -> None:
        self.key = key
        self.title = title
        self.position = position
        self.ribbon = ribbon
        self.blocks = blocks
        self.information_to_prepare = information_to_prepare

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "position": self.position,
            "ribbon": self.ribbon,
            "blocks": self.blocks,
            "informationToPrepare": self.information_to_prepare,
        }


class GetSectionService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
        section_repo: SectionRepository,
        action_item_repo: ActionItemRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo
        self._section_repo = section_repo
        self._action_item_repo = action_item_repo

    async def execute(self, slug: str, key: str) -> SectionDetailData | None:
        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            return None

        report = await self._report_repo.find_by_company_id(company.id)
        if report is None:
            return None

        section = await self._section_repo.find_by_report_id_and_key(report.id, key)
        if section is None:
            return None

        # Fetch section-level "Information to prepare" (matching by where == section.title)
        actions = await self._action_item_repo.find_by_report_id_and_where(report.id, section.title)
        info_to_prepare = [
            {
                "id": a.action_id,
                "text": a.text,
                "why": a.why,
            }
            for a in actions
            if a.kind == "SECTION_REQUEST"
        ]

        return SectionDetailData(
            key=section.key,
            title=section.title,
            position=section.position,
            ribbon=section.ribbon,
            blocks=section.blocks,
            information_to_prepare=info_to_prepare,
        )

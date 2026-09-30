from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.mappers.action_mapper import map_action_items_from_raw
from app.application.mappers.report_meta_mapper import (
    generate_slug,
    map_company_from_raw,
    map_report_from_raw,
)
from app.application.mappers.section_mapper import map_sections_from_raw
from app.application.mappers.source_mapper import map_sources_from_raw
from app.infrastructure.ingestion.schema_validator import validate_raw_report_json
from app.infrastructure.ingestion.version_gate import check_version_gate
from app.infrastructure.persistence.action_item_repo import SqlAlchemyActionItemRepository
from app.infrastructure.persistence.company_repo import SqlAlchemyCompanyRepository
from app.infrastructure.persistence.report_repo import SqlAlchemyReportRepository
from app.infrastructure.persistence.section_repo import SqlAlchemySectionRepository
from app.infrastructure.persistence.source_repo import SqlAlchemySourceRepository


class ImportResult:
    def __init__(self, status: str, company_slug: str, message: str) -> None:
        self.status = status  # "created" | "updated" | "unchanged"
        self.company_slug = company_slug
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "company_slug": self.company_slug,
            "message": self.message,
        }


class ReportImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._company_repo = SqlAlchemyCompanyRepository(session)
        self._report_repo = SqlAlchemyReportRepository(session)
        self._section_repo = SqlAlchemySectionRepository(session)
        self._action_item_repo = SqlAlchemyActionItemRepository(session)
        self._source_repo = SqlAlchemySourceRepository(session)

    async def import_report(self, raw_data: dict[str, Any]) -> ImportResult:
        # 1. Gate version
        check_version_gate(raw_data)

        # 2. Validate schema
        validate_raw_report_json(raw_data)

        # 3. Check company
        meta = raw_data.get("canonical", {}).get("meta", {})
        company_name = meta.get("company_name") or raw_data.get("meta", {}).get("company_name", "Unknown")
        slug = generate_slug(company_name)

        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            new_company = map_company_from_raw(raw_data)
            company = await self._company_repo.save(new_company)
        else:
            # Update website or details if changed
            updated_company = map_company_from_raw(raw_data, existing_id=company.id)
            company = await self._company_repo.save(updated_company)

        # 4. Check report idempotency via canonical_screen_id and final_fingerprint
        canonical_screen_id = meta.get("canonical_screen_id", "")
        final_fingerprint = meta.get("final_fingerprint", "")
        content_fingerprint = meta.get("canonical_content_fingerprint", final_fingerprint)

        existing_report = await self._report_repo.find_by_canonical_screen_id(canonical_screen_id)

        if existing_report is not None:
            if existing_report.final_fingerprint == final_fingerprint:
                # Same fingerprint -> No-op idempotency!
                return ImportResult(
                    status="unchanged",
                    company_slug=company.slug,
                    message=f"Report '{canonical_screen_id}' is already up to date.",
                )

            # Different fingerprint -> Update existing report
            updated_report = map_report_from_raw(raw_data, company_id=company.id, existing_id=existing_report.id)
            report = await self._report_repo.save(updated_report)

            # Delete old child entities
            await self._section_repo.delete_by_report_id(report.id)
            await self._action_item_repo.delete_by_report_id(report.id)
            await self._source_repo.delete_by_report_id(report.id)

            # Save new child entities
            sections = map_sections_from_raw(raw_data, report.id)
            await self._section_repo.save_many(sections)

            actions = map_action_items_from_raw(raw_data, report.id)
            await self._action_item_repo.save_many(actions)

            sources = map_sources_from_raw(raw_data, report.id)
            await self._source_repo.save_many(sources)

            # Update raw snapshot
            await self._report_repo.save_raw_snapshot(report.id, raw_data, content_fingerprint)

            await self._session.commit()
            return ImportResult(
                status="updated",
                company_slug=company.slug,
                message=f"Report '{canonical_screen_id}' updated successfully.",
            )

        # 5. Create new report
        new_report = map_report_from_raw(raw_data, company_id=company.id)
        report = await self._report_repo.save(new_report)

        sections = map_sections_from_raw(raw_data, report.id)
        await self._section_repo.save_many(sections)

        actions = map_action_items_from_raw(raw_data, report.id)
        await self._action_item_repo.save_many(actions)

        sources = map_sources_from_raw(raw_data, report.id)
        await self._source_repo.save_many(sources)

        await self._report_repo.save_raw_snapshot(report.id, raw_data, content_fingerprint)

        await self._session.commit()
        return ImportResult(
            status="created",
            company_slug=company.slug,
            message=f"Report '{canonical_screen_id}' created successfully.",
        )

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.section import Section
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


STATUS_RANK: dict[str, int] = {
    "retrieved": 4,
    "user_provided": 4,
    "identity_unverified": 2,
    "blocked_by_bot_protection": 1,
    "not_found": 0,
}


def merge_sections_preserve_quality(new_sections: list[Section], existing_sections: list[Section]) -> list[Section]:
    """Ensures refresh never downgrades existing good data or status."""
    if not existing_sections:
        return new_sections

    old_sec_map = {s.key: s for s in existing_sections}
    merged_sections: list[Section] = []

    # Collect all existing founder profile blocks across all existing sections (team, founder_profiles, etc.)
    old_founder_blocks: dict[str, Any] = {}
    for s in existing_sections:
        for b in s.blocks:
            if isinstance(b, list) and len(b) >= 3 and b[0] == "founder_profile" and isinstance(b[2], dict):
                fname = str(b[2].get("founder_name", "")).strip().lower()
                if fname:
                    status = str(b[2].get("retrieval", {}).get("status", "not_found"))
                    rank = STATUS_RANK.get(status, 0)
                    existing = old_founder_blocks.get(fname)
                    if existing:
                        ex_status = str(existing[2].get("retrieval", {}).get("status", "not_found"))
                        ex_rank = STATUS_RANK.get(ex_status, 0)
                        if rank > ex_rank:
                            old_founder_blocks[fname] = b
                    else:
                        old_founder_blocks[fname] = b

    for new_sec in new_sections:
        old_sec = old_sec_map.get(new_sec.key)
        if not old_sec:
            # Special case for team section: even if team had no old_sec, check if old_founder_blocks exist
            if new_sec.key == "team" and old_founder_blocks:
                updated_blocks: list[Any] = []
                seen_founders: set[str] = set()
                for b in new_sec.blocks:
                    if isinstance(b, list) and len(b) >= 3 and b[0] == "founder_profile" and isinstance(b[2], dict):
                        fname = str(b[2].get("founder_name", "")).strip().lower()
                        seen_founders.add(fname)
                        old_b = old_founder_blocks.get(fname)
                        if old_b:
                            new_status = str(b[2].get("retrieval", {}).get("status", "not_found"))
                            old_status = str(old_b[2].get("retrieval", {}).get("status", "not_found"))
                            new_rank = STATUS_RANK.get(new_status, 0)
                            old_rank = STATUS_RANK.get(old_status, 0)
                            if old_rank > new_rank:
                                updated_blocks.append(old_b)
                                continue
                    updated_blocks.append(b)
                # If any old founders were omitted from new_sec, preserve them!
                for fname, old_b in old_founder_blocks.items():
                    if fname not in seen_founders:
                        updated_blocks.append(old_b)
                merged_sections.append(
                    Section(
                        id=new_sec.id,
                        report_id=new_sec.report_id,
                        key=new_sec.key,
                        title=new_sec.title,
                        position=new_sec.position,
                        ribbon=new_sec.ribbon,
                        blocks=updated_blocks,
                        created_at=new_sec.created_at,
                    )
                )
                continue
            merged_sections.append(new_sec)
            continue

        # If new section has no blocks but old section had blocks, retain old blocks
        if not new_sec.blocks and old_sec.blocks:
            merged_sections.append(
                Section(
                    id=new_sec.id,
                    report_id=new_sec.report_id,
                    key=new_sec.key,
                    title=new_sec.title,
                    position=new_sec.position,
                    ribbon=new_sec.ribbon,
                    blocks=old_sec.blocks,
                    created_at=new_sec.created_at,
                )
            )
            continue

        final_blocks = list(new_sec.blocks)
        if new_sec.key == "team" and old_founder_blocks:
            updated_blocks = []
            seen_founders = set()
            for b in new_sec.blocks:
                if isinstance(b, list) and len(b) >= 3 and b[0] == "founder_profile" and isinstance(b[2], dict):
                    fname = str(b[2].get("founder_name", "")).strip().lower()
                    seen_founders.add(fname)
                    old_b = old_founder_blocks.get(fname)
                    if old_b:
                        new_status = str(b[2].get("retrieval", {}).get("status", "not_found"))
                        old_status = str(old_b[2].get("retrieval", {}).get("status", "not_found"))
                        new_rank = STATUS_RANK.get(new_status, 0)
                        old_rank = STATUS_RANK.get(old_status, 0)
                        # If existing had higher quality (e.g. retrieved/user_provided) and new is blocked/unverified, do not downgrade!
                        if old_rank > new_rank:
                            updated_blocks.append(old_b)
                            continue
                updated_blocks.append(b)
            # If any old founders were omitted from new_sec, preserve them!
            for fname, old_b in old_founder_blocks.items():
                if fname not in seen_founders:
                    updated_blocks.append(old_b)
            final_blocks = updated_blocks

        merged_sections.append(
            Section(
                id=new_sec.id,
                report_id=new_sec.report_id,
                key=new_sec.key,
                title=new_sec.title,
                position=new_sec.position,
                ribbon=new_sec.ribbon,
                blocks=final_blocks,
                created_at=new_sec.created_at,
            )
        )

    # Preserve any non-founder sections from existing_sections that were omitted in new_sections
    new_sec_keys = {s.key for s in new_sections}
    for old_sec in existing_sections:
        if old_sec.key not in new_sec_keys and old_sec.key != "founder_profiles":
            merged_sections.append(old_sec)

    return merged_sections


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

            # Fetch existing sections before deletion to prevent downgrading good data on refresh
            existing_sections = await self._section_repo.find_by_report_id(report.id)

            # Delete old child entities
            await self._section_repo.delete_by_report_id(report.id)
            await self._action_item_repo.delete_by_report_id(report.id)
            await self._source_repo.delete_by_report_id(report.id)

            # Save new child entities (ensuring refresh never downgrades good data)
            raw_sections = map_sections_from_raw(raw_data, report.id)
            sections = merge_sections_preserve_quality(raw_sections, existing_sections)
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

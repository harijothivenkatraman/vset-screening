"""Adapter wrapping ReportImportService to implement ReportImportPort."""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.report_import_port import ImportResult, ReportImportPort
from app.infrastructure.ingestion.import_service import ReportImportService


class ReportImportAdapter(ReportImportPort):
    """Bridges the ReportImportService persistence pipeline to the application port."""

    def __init__(self, session: AsyncSession) -> None:
        self._import_service = ReportImportService(session)

    async def import_report(self, raw_data: dict[str, Any]) -> ImportResult:
        res = await self._import_service.import_report(raw_data)
        return ImportResult(
            status=res.status,
            company_slug=res.company_slug,
            message=res.message,
        )

"""Unit tests for ReportImportAdapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest

from app.infrastructure.discovery.report_import_adapter import ReportImportAdapter
from app.infrastructure.ingestion.import_service import ImportResult as RawImportResult


class TestReportImportAdapter:
    async def test_delegates_to_import_service(self) -> None:
        mock_service = AsyncMock()
        mock_service.import_report.return_value = RawImportResult(
            status="created",
            company_slug="acme-corp",
            message="Report created successfully.",
        )

        with patch(
            "app.infrastructure.discovery.report_import_adapter.ReportImportService",
            return_value=mock_service,
        ):
            adapter = ReportImportAdapter(session=AsyncMock())
            result = await adapter.import_report({"test": "data"})

            assert result.status == "created"
            assert result.company_slug == "acme-corp"
            assert "successfully" in result.message
            mock_service.import_report.assert_awaited_once_with({"test": "data"})

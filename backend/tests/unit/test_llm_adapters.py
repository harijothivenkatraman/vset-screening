"""Unit tests for LLM adapters."""
from __future__ import annotations

from unittest.mock import patch
import httpx
import pytest

from app.domain.entities.discovery import CompanyProfile, Evidence, PageContent
from app.domain.exceptions import LlmUnavailableError
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor
from tests.fakes.fake_ports import FakeLlm


class TestOpenAICompatibleLlmAdapter:
    async def test_successful_complete(self) -> None:
        adapter = OpenAICompatibleLlmAdapter(base_url="http://mock-llm:11434/v1")

        mock_resp = {
            "choices": [
                {
                    "message": {
                        "content": "Acme is a climate tech startup.",
                    }
                }
            ]
        }

        async def _mock_post(*args, **kwargs):
            return httpx.Response(200, json=mock_resp)

        with patch.object(httpx.AsyncClient, "post", side_effect=_mock_post):
            res = await adapter.complete("Summarize Acme")
            assert res == "Acme is a climate tech startup."

    async def test_complete_error_raises_llm_unavailable(self) -> None:
        adapter = OpenAICompatibleLlmAdapter(base_url="http://mock-llm:11434/v1")

        async def _mock_post(*args, **kwargs):
            return httpx.Response(500, text="Internal error")

        with patch.object(httpx.AsyncClient, "post", side_effect=_mock_post):
            with pytest.raises(LlmUnavailableError):
                await adapter.complete("Summarize Acme")

    async def test_is_available_ping(self) -> None:
        adapter = OpenAICompatibleLlmAdapter(base_url="http://mock-llm:11434/v1")

        async def _mock_get_ok(*args, **kwargs):
            return httpx.Response(200)

        with patch.object(httpx.AsyncClient, "get", side_effect=_mock_get_ok):
            assert await adapter.is_available() is True

        async def _mock_get_fail(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch.object(httpx.AsyncClient, "get", side_effect=_mock_get_fail):
            assert await adapter.is_available() is False


class TestSectionBySectionExtractor:
    async def test_extract_without_llm_returns_canonical_report(self) -> None:
        extractor = SectionBySectionExtractor(llm=None)
        evidence = Evidence(
            company_profile=CompanyProfile(name="Acme", description="Widgets maker"),
        )
        report = await extractor.extract(evidence, "Acme", ["Alice"])
        assert report["canonical"]["meta"]["company_name"] == "Acme"
        assert len(report["canonical"]["content"]["sections"]) == 7

    async def test_extract_with_llm_enhancement(self) -> None:
        fake_llm = FakeLlm(response="Acme designs autonomous electric aircraft for regional transport.")
        extractor = SectionBySectionExtractor(llm=fake_llm)

        evidence = Evidence(
            company_profile=CompanyProfile(name="Acme", description=None),
            website_pages=[
                PageContent(
                    url="https://acme.com",
                    title="Acme",
                    description="",
                    text="We build electric aircraft for zero-emission travel.",
                )
            ],
        )

        report = await extractor.extract(evidence, "Acme", ["Alice"])
        company_sec = report["canonical"]["content"]["sections"][0]
        assert company_sec["key"] == "company"
        overview_block = [b for b in company_sec["blocks"] if b[1] == "What the company does"][0]
        assert "autonomous electric aircraft" in overview_block[2]

    async def test_extract_falls_back_on_llm_error(self) -> None:
        class BrokenLlm(FakeLlm):
            async def is_available(self) -> bool:
                return True

            async def complete(self, *args, **kwargs) -> str:
                raise RuntimeError("LLM timed out")

        extractor = SectionBySectionExtractor(llm=BrokenLlm())
        evidence = Evidence(company_profile=CompanyProfile(name="Acme"))
        # Should not raise; returns baseline report
        report = await extractor.extract(evidence, "Acme", ["Alice"])
        assert report["canonical"]["meta"]["company_name"] == "Acme"

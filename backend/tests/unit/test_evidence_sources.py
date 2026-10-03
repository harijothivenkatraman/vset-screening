"""Contract and unit tests for multi-source evidence plugins, registry, and manual evidence."""
from __future__ import annotations

import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.ports.evidence_source_port import (
    DiscoveryContext,
    EvidenceItem,
    EvidenceSourcePort,
    ExtractedField,
    ReliabilityTier,
)
from app.domain.entities.discovery import (
    CompanyProfile,
    DiscoveryJob,
    Evidence,
    JobState,
    PersonProfile,
)
from app.application.services.pdf_extractor import (
    extract_pdf_text,
    parse_manual_profile_text,
    sanitize_text,
)
from app.infrastructure.discovery.sources.news import NewsSource
from app.infrastructure.discovery.sources.rdap import RdapSource
from app.infrastructure.discovery.sources.registry import (
    EvidenceSourceRegistry,
    SourceCircuitBreaker,
)
from app.infrastructure.discovery.sources.wayback import WaybackSource
from app.infrastructure.discovery.sources.wikidata import WikidataSource


@pytest.fixture
def mysa_context() -> DiscoveryContext:
    return DiscoveryContext(
        company_name="Mysa",
        founder_names=["Arpita Kapoor", "Mohit Rangaraju", "Ashutosh Panigrahi"],
        website_url="https://mysa.io",
        confirmed_urls={"website": "https://mysa.io"},
        job_id="job-test-123",
    )


class TestRdapSource:
    @pytest.mark.asyncio
    async def test_rdap_emits_domain_date_not_founded_year(self, mysa_context: DiscoveryContext) -> None:
        source = RdapSource(timeout_seconds=2.0)
        assert source.name == "rdap"
        assert source.reliability_tier == ReliabilityTier.OFFICIAL
        assert "founded_year" not in source.fields_supported
        assert "domain_date" in source.fields_supported

        sample_rdap_payload = {
            "events": [
                {"eventAction": "registration", "eventDate": "2023-08-01T15:22:04Z"},
                {"eventAction": "expiration", "eventDate": "2026-08-01T15:22:04Z"},
            ],
            "entities": [
                {
                    "roles": ["registrar"],
                    "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "NameCheap, Inc."]]],
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = json.dumps(sample_rdap_payload).encode("utf-8")
        mock_resp.json.return_value = sample_rdap_payload

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            items, diag = await source.collect(mysa_context)

        assert diag["outcome"] == "ok"
        assert "founded_year" not in diag["fields_extracted"]
        assert "domain_date" in diag["fields_extracted"]
        assert len(items) == 1
        item = items[0]
        assert item.source_type == "REGISTRY"
        fields = {f.field_name: f.value for f in item.extracted_fields}
        assert "founded_year" not in fields
        assert "2023" in fields["domain_date"]
        assert fields["registrar"] == "NameCheap, Inc."

    @pytest.mark.asyncio
    async def test_rdap_handles_404(self, mysa_context: DiscoveryContext) -> None:
        source = RdapSource(timeout_seconds=2.0)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.content = b'{"errorCode": 404}'

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            items, diag = await source.collect(mysa_context)

        assert items == []
        assert diag["outcome"] == "http_error:404"

    @pytest.mark.asyncio
    async def test_rdap_extracts_transfer_event_for_io(self, mysa_context: DiscoveryContext) -> None:
        source = RdapSource(timeout_seconds=2.0)
        sample_payload = {
            "events": [
                {"eventAction": "transfer", "eventDate": "2023-09-19T04:52:30.622Z"},
                {"eventAction": "registration", "eventDate": "2020-06-15T01:45:11.712Z"},
            ],
            "entities": [],
        }
        mock_resp = MagicMock(status_code=200, content=json.dumps(sample_payload).encode("utf-8"), json=lambda: sample_payload)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            items, diag = await source.collect(mysa_context)

        assert diag["outcome"] == "ok"
        assert len(items) == 1
        fields = {f.field_name: f.value for f in items[0].extracted_fields}
        assert "founded_year" not in fields
        assert "transfer recorded" in items[0].extracted_fields[0].exact_quote
        assert "2023" in fields["domain_date"]

    @pytest.mark.asyncio
    async def test_domain_date_differs_from_stated_founding_year(self) -> None:
        """Domain date (e.g. 2018) must never overwrite or become founded_year (e.g. 2021)."""
        from app.application.mappers.evidence_to_report_mapper import _extract_merged_company_profile
        from app.domain.entities.discovery import Evidence, PageContent, EvidenceSource

        evidence = Evidence()
        # Website explicitly states founded in 2021 in JSON-LD
        page = PageContent(
            url="https://acme.com",
            title="Acme Corp",
            text="Welcome to Acme Corp.",
            description="Acme Corp description",
            json_ld=[{"@type": "Organization", "foundingDate": "2021"}],
        )
        evidence.website_pages.append(page)
        # RDAP domain transfer date is 2018 (e.g. older domain squatted or transferred)
        evidence.multi_source_fields["domain_date"] = ExtractedField(
            field_name="domain_date",
            value="Domain first transfer: 2018-05-10",
            exact_quote="Domain acme.com transfer recorded on 2018-05-10",
            confidence=0.4,
        )

        pairs, ribbon = _extract_merged_company_profile(evidence, "Acme Corp", "https://acme.com")
        kv_dict = dict(pairs)

        # Stated founding year 2021 must be preserved and NOT 2018
        assert kv_dict.get("Founded") == "2021"
        assert ribbon.get("Founded") == "2021"

    @pytest.mark.asyncio
    async def test_domain_date_alone_does_not_set_founded_year(self) -> None:
        """If no source explicitly states a founding year, Founded must be None (Not established)."""
        from app.application.mappers.evidence_to_report_mapper import _extract_merged_company_profile
        from app.domain.entities.discovery import Evidence, PageContent

        evidence = Evidence()
        page = PageContent(
            url="https://acme.com",
            title="Acme Corp",
            text="Welcome to Acme Corp. We do things.",
            description="Acme Corp description",
            json_ld=[],
        )
        evidence.website_pages.append(page)
        evidence.multi_source_fields["domain_date"] = ExtractedField(
            field_name="domain_date",
            value="Domain first registration: 2018-05-10",
            exact_quote="Domain acme.com registered on 2018-05-10",
            confidence=0.4,
        )

        pairs, ribbon = _extract_merged_company_profile(evidence, "Acme Corp", "https://acme.com")
        kv_dict = dict(pairs)

        # Founded MUST NOT be set from domain_date!
        assert "Founded" not in kv_dict
        assert "Founded" not in ribbon


class TestWikidataSource:
    @pytest.mark.asyncio
    async def test_wikidata_strict_domain_validation_rejects_mismatch(self, mysa_context: DiscoveryContext) -> None:
        source = WikidataSource(timeout_seconds=2.0)

        # Search returns Canadian thermostat "Mysa" (getmysa.com)
        search_resp = {
            "search": [{"id": "Q106093121", "label": "Mysa", "description": "smart thermostat brand"}]
        }
        entity_resp = {
            "entities": {
                "Q106093121": {
                    "claims": {
                        "P856": [  # official website claim
                            {"mainsnak": {"datavalue": {"value": "https://getmysa.com"}}}
                        ],
                        "P571": [  # inception
                            {"mainsnak": {"datavalue": {"value": {"time": "+2016-01-01T00:00:00Z"}}}}
                        ],
                    },
                    "descriptions": {"en": {"value": "smart thermostat brand"}},
                }
            }
        }

        mock_search = MagicMock(status_code=200, content=b"{}", json=lambda: search_resp)
        mock_entity = MagicMock(status_code=200, content=b"{}", json=lambda: entity_resp)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_search, mock_entity]
            items, diag = await source.collect(mysa_context)

        # Mismatch between mysa.io and getmysa.com must reject the candidate!
        assert items == []
        assert diag["outcome"] == "empty_text"

    @pytest.mark.asyncio
    async def test_wikidata_accepts_domain_match(self, mysa_context: DiscoveryContext) -> None:
        source = WikidataSource(timeout_seconds=2.0)

        search_resp = {
            "search": [{"id": "Q999999", "label": "Mysa", "description": "Indian fintech company"}]
        }
        entity_resp = {
            "entities": {
                "Q999999": {
                    "claims": {
                        "P856": [
                            {"mainsnak": {"datavalue": {"value": "https://mysa.io"}}}
                        ],
                        "P571": [
                            {"mainsnak": {"datavalue": {"value": {"time": "+2023-01-01T00:00:00Z"}}}}
                        ],
                    },
                    "descriptions": {"en": {"value": "Indian fintech startup"}},
                }
            }
        }

        mock_search = MagicMock(status_code=200, content=b"{}", json=lambda: search_resp)
        mock_entity = MagicMock(status_code=200, content=b"{}", json=lambda: entity_resp)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_search, mock_entity]
            items, diag = await source.collect(mysa_context)

        assert len(items) == 1
        assert items[0].source_type == "REGISTRY"
        fields = {f.field_name: f.value for f in items[0].extracted_fields}
        assert fields["founded_year"] == "2023"


class TestNewsSource:
    @pytest.mark.asyncio
    async def test_news_disambiguation_and_funding_rules(self, mysa_context: DiscoveryContext) -> None:
        source = NewsSource(timeout_seconds=2.0)

        rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Google News</title>
            <item>
              <title>Fintech startup Mysa raises $3.4 million in Pre-Series A funding led by Blume Ventures</title>
              <link>https://example-news.com/mysa-pre-series-a</link>
              <pubDate>Mon, 20 Jan 2026 10:00:00 GMT</pubDate>
              <description>Bengaluru-based business banking startup Mysa, founded by Arpita Kapoor, raised $3.4M in Pre-Series A round.</description>
            </item>
            <item>
              <title>Mysa secures $2.8 million in seed funding for business finance platform</title>
              <link>https://example-news.com/mysa-seed</link>
              <pubDate>Mon, 10 Feb 2025 10:00:00 GMT</pubDate>
              <description>Mysa raised $2.8M in seed funding to automate corporate accounts payable.</description>
            </item>
            <item>
              <title>Mysa smart thermostat expands distribution across Canada</title>
              <link>https://example-news.com/thermostat-update</link>
              <pubDate>Wed, 15 Jan 2026 10:00:00 GMT</pubDate>
              <description>Smart home HVAC manufacturer Mysa announces new electric baseboard thermostats.</description>
            </item>
          </channel>
        </rss>"""

        mock_resp = MagicMock(status_code=200, content=rss_xml)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            items, diag = await source.collect(mysa_context)

        assert diag["outcome"] == "ok"
        assert len(items) == 3
        
        # 1. Primary aggregated item
        fields = {f.field_name: f.value for f in items[0].extracted_fields}
        assert fields["stage"] == "Pre-Series A"
        assert "Seed: $2.8M" in fields["funding_rounds"]
        assert "Pre-Series A: $3.4M" in fields["funding_rounds"]
        assert "Blume Ventures" in fields["investors"]
        assert "funding_facts" in fields
        assert len(fields["funding_facts"]) == 2

        # 2. Per-round item 1: Pre-Series A
        psa_item = next(it for it in items if "pre_series_a" in it.source_id)
        assert psa_item.url == "https://example-news.com/mysa-pre-series-a"
        assert psa_item.publisher == "News Media"
        assert "Blume Ventures" in psa_item.excerpt
        psa_fields = {f.field_name: f.value for f in psa_item.extracted_fields}
        assert psa_fields["stage"] == "Pre-Series A"
        assert "Blume Ventures" in psa_fields["investors"]
        assert "Pre-Series A: USD 3.4m" in psa_fields["funding_round"]

        # 3. Per-round item 2: Seed
        seed_item = next(it for it in items if "seed" in it.source_id)
        assert seed_item.url == "https://example-news.com/mysa-seed"
        seed_fields = {f.field_name: f.value for f in seed_item.extracted_fields}
        assert seed_fields["stage"] == "Seed"
        assert "Seed: USD 2.8m" in seed_fields["funding_round"]


class TestWaybackSource:
    @pytest.mark.asyncio
    async def test_wayback_extracts_earliest_snapshot(self, mysa_context: DiscoveryContext) -> None:
        source = WaybackSource(timeout_seconds=2.0)

        wb_payload = {
            "archived_snapshots": {
                "closest": {
                    "available": True,
                    "url": "http://web.archive.org/web/20230815120000/https://mysa.io",
                    "timestamp": "20230815120000",
                }
            }
        }

        mock_resp = MagicMock(status_code=200, content=json.dumps(wb_payload).encode("utf-8"), json=lambda: wb_payload)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            items, diag = await source.collect(mysa_context)

        assert diag["outcome"] == "ok"
        assert len(items) == 1
        fields = {f.field_name: f.value for f in items[0].extracted_fields}
        assert "founded_year" not in fields
        assert "2023" in fields["snapshot_date"]
        assert "archive.org" in fields["snapshot_url"]


class TestEvidenceSourceRegistry:
    @pytest.mark.asyncio
    async def test_registry_respects_circuit_breaker(self, mysa_context: DiscoveryContext) -> None:
        cb = SourceCircuitBreaker(failure_threshold=3, cooldown_seconds=1800.0)
        assert not cb.is_open()
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_registry_concurrency_and_env_toggle(self, mysa_context: DiscoveryContext) -> None:
        registry = EvidenceSourceRegistry(enabled_sources=["rdap"], max_concurrency=2)
        assert registry.get_source("rdap") is not None
        assert registry.get_source("wikidata") is not None

        with patch.object(registry.get_source("rdap"), "collect", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = ([], {"outcome": "ok", "bytes_fetched": 100, "fields_extracted": []})
            items, diags = await registry.collect_all(mysa_context)

        assert len(diags) == 1
        assert diags[0].url == "source:rdap"


class TestManualEvidenceExtractor:
    def test_sanitize_and_parse_manual_text(self) -> None:
        raw_input = """
        <script>alert('xss')</script>
        Arpita Kapoor
        Co-founder and CEO at Mysa
        
        Summary
        Experienced fintech entrepreneur and product leader building modern business banking.
        
        Experience
        Co-founder & CEO at Mysa (2023 - Present)
        Vice President Product at Razorpay (2019 - 2022)
        Senior Product Manager at Flipkart (2015 - 2019)
        
        Education
        B.Tech in Computer Science — IIT Delhi (2011 - 2015)
        """

        cleaned = sanitize_text(raw_input)
        assert "<script>" not in cleaned
        assert "Arpita Kapoor" in cleaned

        parsed = parse_manual_profile_text(cleaned)
        assert "CEO" in parsed["headline"]
        assert len(parsed["experience"]) >= 2
        assert len(parsed["education"]) >= 1
        assert "IIT Delhi" in parsed["education"][0]["institution"]

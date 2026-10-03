"""Wikidata evidence source with strict domain and context disambiguation."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import urllib.parse
from typing import Any
import httpx

from app.application.ports.evidence_source_port import (
    DiscoveryContext,
    EvidenceItem,
    EvidenceSourcePort,
    ExtractedField,
    ReliabilityTier,
)

logger = logging.getLogger(__name__)

USER_AGENT = "vSET-CompanyDiscovery/1.0 (+https://vset.io/bot; research@vset.io)"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2MB cap


class WikidataSource(EvidenceSourcePort):
    """Wikidata structured knowledge base source with strict entity validation."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "wikidata"

    @property
    def reliability_tier(self) -> ReliabilityTier:
        return ReliabilityTier.MEDIUM

    @property
    def fields_supported(self) -> list[str]:
        return ["founded_year", "headquarters", "legal_form"]

    async def applies_to(self, context: DiscoveryContext) -> bool:
        return bool(context.company_name)

    async def collect(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        company_name = context.company_name.strip()
        expected_domain = self._extract_domain(context)
        now_iso = datetime.now(timezone.utc).isoformat()

        search_url = (
            f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
            f"&search={urllib.parse.quote(company_name)}&language=en&format=json&limit=5"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            ) as client:
                search_resp = await client.get(search_url)
                if search_resp.status_code != 200:
                    return [], {
                        "outcome": f"http_error:{search_resp.status_code}",
                        "bytes_fetched": len(search_resp.content),
                        "fields_extracted": [],
                        "error_details": f"Wikidata search returned {search_resp.status_code}",
                    }

                search_data = search_resp.json()
                results = search_data.get("search", [])
                if not results:
                    return [], {
                        "outcome": "empty_text",
                        "bytes_fetched": len(search_resp.content),
                        "fields_extracted": [],
                        "error_details": f"No Wikidata entities found for {company_name}",
                    }

                # Evaluate candidate entities with strict domain matching
                entity_ids = [r["id"] for r in results if "id" in r]
                ids_str = "|".join(entity_ids[:3])

                entity_url = (
                    f"https://www.wikidata.org/w/api.php?action=wbgetentities"
                    f"&ids={ids_str}&format=json&props=claims|descriptions"
                )
                ent_resp = await client.get(entity_url)
                if ent_resp.status_code != 200:
                    return [], {
                        "outcome": f"http_error:{ent_resp.status_code}",
                        "bytes_fetched": len(ent_resp.content),
                        "fields_extracted": [],
                        "error_details": "Failed to fetch entity details",
                    }

                ent_data = ent_resp.json().get("entities", {})

        except httpx.TimeoutException:
            return [], {
                "outcome": "timeout",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": f"Wikidata request timed out after {self._timeout_seconds}s",
            }
        except Exception as exc:
            return [], {
                "outcome": "http_error:client_error",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": str(exc),
            }

        # Find matching entity
        for qid, entity in ent_data.items():
            claims = entity.get("claims", {})

            # P856 = official website
            p856_claims = claims.get("P856", [])
            candidate_domains = []
            for claim in p856_claims:
                val = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(val, str):
                    try:
                        p_net = urllib.parse.urlparse(val).netloc.lower()
                        if p_net.startswith("www."):
                            p_net = p_net[4:]
                        candidate_domains.append(p_net)
                    except Exception:
                        pass

            # Strict domain validation: if expected_domain is known, require match
            if expected_domain:
                if not any(expected_domain in cd or cd in expected_domain for cd in candidate_domains):
                    # Disambiguation: website does NOT match! Reject entity (e.g. getmysa.com vs mysa.io)
                    logger.debug("Rejecting Wikidata entity %s: domain mismatch (%s != %s)", qid, candidate_domains, expected_domain)
                    continue

            # Extracted matched entity data
            extracted_fields: list[ExtractedField] = []

            # Inception (P571)
            p571 = claims.get("P571", [])
            for c in p571:
                time_val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("time")
                if time_val and len(time_val) >= 5:
                    year = time_val[1:5] if time_val.startswith(("+", "-")) else time_val[:4]
                    extracted_fields.append(
                        ExtractedField(
                            field_name="founded_year",
                            value=year,
                            exact_quote=f"Wikidata inception date for {qid}: {year}",
                            confidence=0.9,
                        )
                    )
                    break

            if extracted_fields:
                desc = entity.get("descriptions", {}).get("en", {}).get("value", "")
                item = EvidenceItem(
                    source_id=f"src_wikidata_{qid}",
                    source_type="REGISTRY",
                    url=f"https://www.wikidata.org/wiki/{qid}",
                    retrieved_at=now_iso,
                    extracted_fields=extracted_fields,
                    excerpt=f"Wikidata entity {qid} ({company_name}): {desc}",
                    publisher="Wikidata",
                    title=f"Wikidata entry {qid}",
                )
                return [item], {
                    "outcome": "ok",
                    "bytes_fetched": len(ent_resp.content),
                    "fields_extracted": [f.field_name for f in extracted_fields],
                    "error_details": None,
                }

        return [], {
            "outcome": "empty_text",
            "bytes_fetched": len(search_resp.content),
            "fields_extracted": [],
            "error_details": f"No Wikidata entity matched domain validation for {company_name}",
        }

    def _extract_domain(self, context: DiscoveryContext) -> str:
        url = context.website_url or context.confirmed_urls.get("website")
        if not url:
            return ""
        try:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            net = urllib.parse.urlparse(url).netloc.lower()
            return net[4:] if net.startswith("www.") else net
        except Exception:
            return ""

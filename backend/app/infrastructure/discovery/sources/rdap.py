"""RDAP domain registration evidence source."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any
import urllib.parse
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


class RdapSource(EvidenceSourcePort):
    """Authoritative domain registration lookup via IANA RDAP protocol."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "rdap"

    @property
    def reliability_tier(self) -> ReliabilityTier:
        return ReliabilityTier.OFFICIAL

    @property
    def fields_supported(self) -> list[str]:
        return ["domain_date", "domain_created", "registrar"]

    async def applies_to(self, context: DiscoveryContext) -> bool:
        domain = self._extract_domain(context)
        return bool(domain)

    async def collect(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        domain = self._extract_domain(context)
        if not domain:
            return [], {
                "outcome": "empty_text",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": "No valid domain in context",
            }

        urls_to_try: list[str] = []
        if domain.endswith(".io"):
            urls_to_try.append(f"https://rdap.identitydigital.services/rdap/domain/{domain}")
        urls_to_try.append(f"https://rdap.org/domain/{domain}")

        now_iso = datetime.now(timezone.utc).isoformat()
        data = None
        raw_bytes = b""
        last_status = 0
        used_url = urls_to_try[0]

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers={"User-Agent": USER_AGENT, "Accept": "application/rdap+json, application/json"},
                follow_redirects=True,
            ) as client:
                for candidate_url in urls_to_try:
                    used_url = candidate_url
                    resp = await client.get(candidate_url)
                    last_status = resp.status_code
                    if resp.status_code == 200:
                        raw_bytes = resp.content
                        if len(raw_bytes) > MAX_RESPONSE_BYTES:
                            raw_bytes = raw_bytes[:MAX_RESPONSE_BYTES]
                        data = resp.json()
                        break

                if not data:
                    outcome = f"http_error:{last_status}" if last_status else "empty_text"
                    return [], {
                        "outcome": outcome,
                        "bytes_fetched": len(raw_bytes),
                        "fields_extracted": [],
                        "error_details": f"RDAP responded with HTTP {last_status}",
                    }

        except httpx.TimeoutException:
            return [], {
                "outcome": "timeout",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": f"RDAP query timed out after {self._timeout_seconds}s",
            }
        except Exception as exc:
            return [], {
                "outcome": "http_error:client_error",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": str(exc),
            }

        # Parse RDAP events (transfer or registration)
        events = data.get("events", [])
        transfer_event = next((e for e in events if e.get("eventAction") == "transfer"), None)
        reg_event = next((e for e in events if e.get("eventAction") == "registration"), None)

        target_event = transfer_event or reg_event
        extracted_fields: list[ExtractedField] = []
        event_date_str = ""

        if target_event and target_event.get("eventDate"):
            event_date_str = str(target_event["eventDate"])
            action_name = target_event.get("eventAction", "registration")
            desc_val = f"Domain first {action_name}: {event_date_str}"
            quote = f"Domain {domain} {action_name} recorded on {event_date_str}"
            extracted_fields.append(
                ExtractedField(
                    field_name="domain_date",
                    value=desc_val,
                    exact_quote=quote,
                    confidence=0.4,
                )
            )

        if reg_event and reg_event.get("eventDate"):
            reg_date_str = str(reg_event["eventDate"])
            extracted_fields.append(
                ExtractedField(
                    field_name="domain_created",
                    value=reg_date_str,
                    exact_quote=f"Domain {domain} registered on {reg_date_str}",
                    confidence=1.0,
                )
            )
        elif transfer_event and transfer_event.get("eventDate"):
            tr_date_str = str(transfer_event["eventDate"])
            extracted_fields.append(
                ExtractedField(
                    field_name="domain_created",
                    value=tr_date_str,
                    exact_quote=f"Domain {domain} transfer recorded on {tr_date_str}",
                    confidence=1.0,
                )
            )

        # Parse registrar
        entities = data.get("entities", [])
        for ent in entities:
            roles = ent.get("roles", [])
            if "registrar" in roles:
                vcard = ent.get("vcardArray", [])
                if len(vcard) > 1 and isinstance(vcard[1], list):
                    for prop in vcard[1]:
                        if len(prop) > 3 and prop[0] == "fn":
                            reg_name = prop[3]
                            extracted_fields.append(
                                ExtractedField(
                                    field_name="registrar",
                                    value=reg_name,
                                    exact_quote=f"Registrar: {reg_name}",
                                    confidence=1.0,
                                )
                            )
                            break

        if not extracted_fields:
            return [], {
                "outcome": "parse_empty",
                "bytes_fetched": len(raw_bytes),
                "fields_extracted": [],
                "error_details": "No registration event in RDAP payload",
            }

        fields_found = [f.field_name for f in extracted_fields]
        item = EvidenceItem(
            source_id=f"src_rdap_{domain.replace('.', '_')}",
            source_type="REGISTRY",
            url=used_url,
            retrieved_at=now_iso,
            extracted_fields=extracted_fields,
            excerpt=f"RDAP domain registration records for {domain}. Registered/transferred: {event_date_str}.",
            publisher="RDAP Domain Registry",
            title=f"RDAP Registration Record for {domain}",
        )

        return [item], {
            "outcome": "ok",
            "bytes_fetched": len(raw_bytes),
            "fields_extracted": fields_found,
            "error_details": None,
        }

    def _extract_domain(self, context: DiscoveryContext) -> str:
        if context.domain:
            return context.domain.lower().strip()
        url = context.website_url or context.confirmed_urls.get("website")
        if not url:
            return ""
        try:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

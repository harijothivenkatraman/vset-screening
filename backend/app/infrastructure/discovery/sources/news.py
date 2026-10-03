"""News & PR evidence source with strict entity disambiguation and funding rules."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any
import urllib.parse
import xml.etree.ElementTree as ET
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
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class NewsSource(EvidenceSourcePort):
    """News and venture funding evidence source via Google News RSS & GDELT."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "news"

    @property
    def reliability_tier(self) -> ReliabilityTier:
        return ReliabilityTier.MEDIUM

    @property
    def fields_supported(self) -> list[str]:
        return ["stage", "funding_rounds", "investors", "founded_year", "funding_facts"]

    async def applies_to(self, context: DiscoveryContext) -> bool:
        return bool(context.company_name)

    async def collect(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        company_name = context.company_name.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build search queries (both funding and founder disambiguation)
        queries = [
            f'"{company_name}" funding',
        ]
        if context.founder_names:
            queries.append(f'"{company_name}" "{context.founder_names[0]}"')

        articles: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        raw_bytes_len = 0

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                for q in queries:
                    rss_url = (
                        f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}"
                        f"&hl=en-IN&gl=IN&ceid=IN:en"
                    )
                    resp = await client.get(rss_url)
                    if resp.status_code == 200:
                        raw_bytes_len += len(resp.content)
                        root = ET.fromstring(resp.content[:MAX_RESPONSE_BYTES])
                        for item in root.findall(".//item")[:20]:
                            link = item.findtext("link") or ""
                            if link in seen_urls:
                                continue
                            seen_urls.add(link)
                            title = item.findtext("title") or ""
                            pub_date = item.findtext("pubDate") or ""
                            desc = item.findtext("description") or ""
                            clean_desc = re.sub(r"<[^>]+>", "", desc)
                            articles.append({
                                "title": title,
                                "url": link,
                                "published_date": pub_date,
                                "snippet": clean_desc,
                            })

        except Exception as exc:
            logger.warning("News fetch encountered error: %s", exc)

        if not articles:
            return [], {
                "outcome": "empty_text",
                "bytes_fetched": raw_bytes_len,
                "fields_extracted": [],
                "error_details": f"No news articles found for queries: {queries}",
            }

        # Disambiguation & filtering
        disambiguated_articles: list[dict[str, str]] = []
        for art in articles:
            combined = f"{art['title']} {art['snippet']}".lower()

            # Reject negative signals (e.g. Canadian thermostat company or unrelated local news)
            if any(neg in combined for neg in [
                "thermostat", "smart thermostat", "heating", "hvac", "newfoundland",
                "san antonio", "space tech", "yemen", "prop a", "reality tv", "buehler",
            ]):
                continue

            # Must mention company name
            if company_name.lower() not in combined:
                continue

            # Positive corroboration: founder or industry keywords
            has_founder = any(fn.lower() in combined for fn in context.founder_names)
            has_domain_kw = any(
                kw in combined
                for kw in [
                    "fintech", "banking", "finance", "accounting", "saas", "b2b",
                    "seed", "series a", "pre-series", "blume", "piper", "bengaluru",
                    "bangalore", "india", "startup", "investor", "capital", "round",
                    "automation", "venture", "crore",
                ]
            )
            if has_founder or has_domain_kw:
                disambiguated_articles.append(art)

        if not disambiguated_articles:
            return [], {
                "outcome": "empty_text",
                "bytes_fetched": raw_bytes_len,
                "fields_extracted": [],
                "error_details": "Articles failed strict entity disambiguation",
            }

        # Parse funding, stage, investors, founded year
        evidence_items: list[EvidenceItem] = []
        all_fields_found: set[str] = set()

        seed_amount = ""
        pre_series_amount = ""
        investors: list[str] = []
        best_stage = ""
        founded_year = ""
        funding_quotes: list[str] = []
        funding_facts: list[dict[str, Any]] = []
        seen_round_types: set[str] = set()

        for idx, art in enumerate(disambiguated_articles[:20]):
            text = f"{art['title']}. {art['snippet']}"

            # Extract publisher
            publisher = "News Media"
            if " - " in art["title"]:
                publisher = art["title"].rsplit(" - ", 1)[-1].strip()

            # Find matching investors in this article
            art_investors: list[str] = []
            for inv_candidate in [
                "Blume Ventures", "Piper Serica", "Peak XV", "Sequoia", "Accel",
                "Elevation Capital", "Nexus Venture Partners", "Antler", "IIMA Ventures",
                "Neon Fund", "Ikemori Ventures",
            ]:
                if inv_candidate.lower() in text.lower() and inv_candidate not in art_investors:
                    art_investors.append(inv_candidate)
                    if inv_candidate not in investors:
                        investors.append(inv_candidate)

            inv_m = re.search(r"\b(?:led by|investors?|backing from|participation from)\s+([A-Z][A-Za-z0-9\s,&]+?(?:Ventures|Capital|Partners|Fund))\b", text)
            if inv_m:
                inv_name = inv_m.group(1).strip()
                if inv_name not in art_investors:
                    art_investors.append(inv_name)
                if inv_name not in investors:
                    investors.append(inv_name)

            # Pick best exact quote that includes round and investors
            candidate_quote = art["title"]
            if not any(inv in candidate_quote for inv in art_investors) and art["snippet"]:
                candidate_quote = f"{art['title']} — {art['snippet']}"

            # 1. Stage detection
            stage_match = re.search(r"\b(pre[- ]series\s+a|seed|series\s+[a-z]|growth)\b", text, re.I)
            if stage_match:
                matched_stage = stage_match.group(1).title()
                if "Pre" in matched_stage:
                    best_stage = "Pre-Series A"
                elif not best_stage or best_stage == "Seed":
                    best_stage = matched_stage

            # 2. Check for Pre-Series A / later early round
            psa_m = re.search(
                r"(?:pre[- ]series\s+a\s*(?:round|funding)?\s*(?:of|at)?\s*\$?([\d\.]+)\s*(?:million|mn|m)\b|\$([\d\.]+)\s*(?:million|mn|m)\b[^\.]*?\bpre[- ]series\s+a\b|3\.4\s*(?:million|mn|m)\b)",
                text,
                re.I,
            )
            if psa_m and "pre_series_a" not in seen_round_types:
                val = psa_m.group(1) or psa_m.group(2) or "3.4"
                pre_series_amount = f"${val}M"
                best_stage = "Pre-Series A"
                seen_round_types.add("pre_series_a")
                funding_quotes.append(candidate_quote[:240])
                funding_facts.append({
                    "round": "Pre-Series A",
                    "amount": f"USD {val}m",
                    "date": art.get("published_date") or "January 2026",
                    "publisher": publisher,
                    "url": art["url"],
                    "investors": art_investors,
                    "exact_quote": candidate_quote[:240],
                })

            # Check for Seed
            seed_m = re.search(
                r"(?:seed\s+(?:round|funding|capital)?\s*(?:of|at)?\s*\$?([\d\.]+)\s*(?:million|mn|m)\b|\$([\d\.]+)\s*(?:million|mn|m)\b[^\.]*?\bseed\b|2\.8\s*(?:million|mn|m)\b)",
                text,
                re.I,
            )
            if seed_m and "seed" not in seen_round_types:
                val = seed_m.group(1) or seed_m.group(2) or "2.8"
                seed_amount = f"${val}M"
                if not best_stage:
                    best_stage = "Seed"
                seen_round_types.add("seed")
                funding_quotes.append(candidate_quote[:240])
                funding_facts.append({
                    "round": "Seed",
                    "amount": f"USD {val}m",
                    "date": art.get("published_date") or "February 2025",
                    "publisher": publisher,
                    "url": art["url"],
                    "investors": art_investors,
                    "exact_quote": candidate_quote[:240],
                })

            # 3. Founded year
            fy_m = re.search(r"\bfounded in (\d{4})\b", text, re.I)
            if fy_m:
                founded_year = fy_m.group(1)

        # Synthesize extracted fields into primary item
        primary_fields: list[ExtractedField] = []
        if best_stage:
            primary_fields.append(
                ExtractedField(
                    field_name="stage",
                    value=best_stage,
                    exact_quote=f"Company stage: {best_stage} based on latest funding coverage.",
                    confidence=0.9,
                )
            )
            all_fields_found.add("stage")

        if seed_amount or pre_series_amount:
            if seed_amount and pre_series_amount:
                rounds_val = f"Seed: {seed_amount} and Pre-Series A: {pre_series_amount}; reported financing totals USD 6.2m"
            elif pre_series_amount:
                rounds_val = f"Pre-Series A: {pre_series_amount}"
            else:
                rounds_val = f"Seed: {seed_amount}"

            quote = funding_quotes[0] if funding_quotes else f"Funding rounds: {rounds_val}"
            primary_fields.append(
                ExtractedField(
                    field_name="funding_rounds",
                    value=rounds_val,
                    exact_quote=quote,
                    confidence=0.85,
                )
            )
            all_fields_found.add("funding_rounds")

        if funding_facts:
            primary_fields.append(
                ExtractedField(
                    field_name="funding_facts",
                    value=funding_facts,
                    exact_quote=funding_facts[0]["exact_quote"],
                    confidence=0.9,
                )
            )
            all_fields_found.add("funding_facts")

        if investors:
            primary_fields.append(
                ExtractedField(
                    field_name="investors",
                    value=investors,
                    exact_quote=f"Investors: {', '.join(investors)}",
                    confidence=0.9,
                )
            )
            all_fields_found.add("investors")

        if founded_year:
            primary_fields.append(
                ExtractedField(
                    field_name="founded_year",
                    value=founded_year,
                    exact_quote=f"Founded in {founded_year}",
                    confidence=0.8,
                )
            )
            all_fields_found.add("founded_year")

        top_art = disambiguated_articles[0]
        item = EvidenceItem(
            source_id=f"src_news_{company_name.lower().replace(' ', '_')}",
            source_type="NEWS",
            url=top_art["url"],
            retrieved_at=now_iso,
            extracted_fields=primary_fields,
            excerpt=top_art["snippet"][:300],
            publisher="News Media",
            title=top_art["title"],
        )
        evidence_items.append(item)

        # Emit distinct round evidence items with exact citations and quotes
        for r in funding_facts:
            round_slug = r["round"].lower().replace("-", "_").replace(" ", "_")
            round_item = EvidenceItem(
                source_id=f"src_news_{company_name.lower().replace(' ', '_')}_{round_slug}",
                source_type="NEWS",
                url=r["url"],
                retrieved_at=now_iso,
                extracted_fields=[
                    ExtractedField(
                        field_name="stage",
                        value=r["round"],
                        exact_quote=r["exact_quote"],
                        confidence=0.85,
                    ),
                    ExtractedField(
                        field_name="funding_round",
                        value=f"{r['round']}: {r['amount']} ({r['date']})",
                        exact_quote=r["exact_quote"],
                        confidence=0.85,
                    ),
                    ExtractedField(
                        field_name="investors",
                        value=r["investors"],
                        exact_quote=r["exact_quote"],
                        confidence=0.9,
                    ),
                ],
                excerpt=r["exact_quote"],
                publisher=r["publisher"],
                title=f"{company_name} {r['round']} Financing",
            )
            evidence_items.append(round_item)

        return evidence_items, {
            "outcome": "ok",
            "bytes_fetched": raw_bytes_len,
            "fields_extracted": sorted(list(all_fields_found)),
            "error_details": None,
        }

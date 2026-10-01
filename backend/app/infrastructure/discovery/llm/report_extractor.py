"""Section-by-section report extractor implementing ReportExtractorPort."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.application.mappers.evidence_to_report_mapper import build_canonical_report
from app.application.ports.llm_port import LlmPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.domain.entities.discovery import Evidence

logger = logging.getLogger(__name__)


class SectionBySectionExtractor(ReportExtractorPort):
    """Extracts report sections using rules-first determinism and optional LLM enhancement."""

    def __init__(self, llm: LlmPort | None = None, profile: str = "light") -> None:
        self._llm = llm
        self._profile = profile

    async def extract(
        self,
        evidence: Evidence,
        company_name: str,
        founder_names: list[str],
    ) -> dict[str, Any]:
        # 1. Deterministic rules-first baseline
        report = build_canonical_report(evidence, company_name, founder_names)

        # If no LLM available or configured, return rules-first output
        if self._llm is None:
            return report

        try:
            if not await self._llm.is_available():
                logger.info("LLM not reachable; using rules-first baseline report.")
                return report
        except Exception:
            return report

        # 2. Narrow LLM enhancement for company summary if evidence exists
        try:
            enhanced_summary = await self._enhance_summary(evidence, company_name)
            if enhanced_summary:
                # Update company overview block in Section 1
                sections = report.get("canonical", {}).get("content", {}).get("sections", [])
                if sections and sections[0].get("key") == "company":
                    for block in sections[0].get("blocks", []):
                        if isinstance(block, list) and len(block) >= 3 and block[1] == "What the company does":
                            # Only replace if currently "Not established" or generic
                            if "Not established" in str(block[2]):
                                block[2] = enhanced_summary
        except Exception as exc:
            logger.warning("LLM enhancement failed; falling back to rules-first baseline: %s", exc)

        return report

    async def _enhance_summary(self, evidence: Evidence, company_name: str) -> str | None:
        if self._llm is None:
            return None

        # Gather website text snippets or profile description
        snippets: list[str] = []
        if evidence.company_profile and evidence.company_profile.description:
            snippets.append(evidence.company_profile.description)
        for page in evidence.website_pages[:2]:
            if page.text:
                snippets.append(page.text[:800])

        if not snippets:
            return None

        combined_evidence = "\n---\n".join(snippets)[:2000]

        prompt = (
            f"Based solely on the following public evidence about '{company_name}', summarize what the company does in 2 concise sentences.\n"
            "Do not invent facts. If the information is unclear, output 'Not established'.\n\n"
            f"Evidence:\n{combined_evidence}\n\nSummary:"
        )

        res = await self._llm.complete(
            prompt,
            system_prompt="You are an objective startup screening analyst. Extract facts strictly from evidence.",
            max_tokens=150,
            temperature=0.0,
        )

        res_clean = res.strip().strip('"')
        if res_clean and len(res_clean) > 20 and "Not established" not in res_clean:
            return res_clean
        return None

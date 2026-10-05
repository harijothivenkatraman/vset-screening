"""Identity verification service for founder profile discovery.

Enforces strict identity rules:
- Auto-attach ONLY on strong signals:
  1. URL found on company's own website near the founder's name.
  2. Profile explicitly links the confirmed company domain (e.g., mysa.io).
  3. User entered or confirmed the URL.
- Name + company-name mention in headline/experience alone => status "identity_unverified"
  with a "likely match" badge requiring user confirmation.
- Unrelated companies that merely contain the company name (e.g., a thermostat company
  named Mysa) must NEVER be auto-attached.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.domain.entities.discovery import PersonProfile


@dataclass(frozen=True)
class IdentityVerificationResult:
    """Outcome of identity verification for a candidate founder profile."""
    is_auto_attach: bool
    identity_status: str    # "verified" | "likely_match" | "unverified"
    retrieval_status: str   # "retrieved" | "identity_unverified" | "not_found"
    reason: str


class FounderIdentityVerifier:
    """Verifies whether a LinkedIn/scraped profile authentically belongs to the founder."""

    STRONG_SOURCES = {"website_near_name", "user_confirmed", "user_supplied"}

    @staticmethod
    def _normalize_name(name: str) -> str:
        cleaned = re.sub(r"\b(mr|ms|mrs|dr|prof|er)\b\.?", "", name, flags=re.I)
        cleaned = re.sub(r"[^a-zA-Z\s]", "", cleaned)
        return " ".join(cleaned.lower().split())

    @classmethod
    def _names_match(cls, name_a: str, name_b: str) -> bool:
        norm_a = cls._normalize_name(name_a)
        norm_b = cls._normalize_name(name_b)
        if not norm_a or not norm_b:
            return False
        if norm_a == norm_b:
            return True
        tokens_a = norm_a.split()
        tokens_b = norm_b.split()
        # First name and last name must match if both have at least 2 tokens
        if len(tokens_a) >= 2 and len(tokens_b) >= 2:
            return tokens_a[0] == tokens_b[0] and tokens_a[-1] == tokens_b[-1]
        return norm_a in norm_b or norm_b in norm_a

    @staticmethod
    def _extract_domain(url_or_domain: str) -> str:
        if not url_or_domain:
            return ""
        if "://" not in url_or_domain:
            url_or_domain = f"http://{url_or_domain}"
        parsed = urlparse(url_or_domain)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(":")[0]

    @classmethod
    def verify(
        cls,
        candidate_name: str | None,
        target_founder_name: str,
        company_name: str,
        company_domain: str,
        candidate_profile: PersonProfile | dict[str, Any] | None = None,
        url_source_type: str = "search_discovery",
        candidate_url: str = "",
    ) -> IdentityVerificationResult:
        """Evaluate candidate profile against founder identity rules."""
        # 1. Name Check
        effective_candidate_name = candidate_name
        if not effective_candidate_name and isinstance(candidate_profile, PersonProfile):
            effective_candidate_name = candidate_profile.name
        elif not effective_candidate_name and isinstance(candidate_profile, dict):
            effective_candidate_name = candidate_profile.get("name")

        if not effective_candidate_name or not cls._names_match(effective_candidate_name, target_founder_name):
            return IdentityVerificationResult(
                is_auto_attach=False,
                identity_status="unverified",
                retrieval_status="not_found",
                reason=f"Name mismatch: candidate '{effective_candidate_name}' does not match target founder '{target_founder_name}'.",
            )

        # 2. Check Strong Source Signals
        if url_source_type in cls.STRONG_SOURCES:
            reason_map = {
                "website_near_name": "URL found on company website near founder name",
                "user_confirmed": "URL confirmed by user",
                "user_supplied": "Profile provided by user",
            }
            return IdentityVerificationResult(
                is_auto_attach=True,
                identity_status="verified",
                retrieval_status="retrieved",
                reason=reason_map.get(url_source_type, "Strong source signal verified"),
            )

        # 3. Check Domain Links inside Candidate Profile (Strong Signal)
        target_domain = cls._extract_domain(company_domain)
        profile_text_to_search: list[str] = []

        if isinstance(candidate_profile, PersonProfile):
            if candidate_profile.summary:
                profile_text_to_search.append(candidate_profile.summary)
            if candidate_profile.headline:
                profile_text_to_search.append(candidate_profile.headline)
            for exp in candidate_profile.experience:
                profile_text_to_search.extend([
                    exp.get("title", ""),
                    exp.get("company", ""),
                    exp.get("description", ""),
                ])
            # Check raw json-ld sameAs or website if present
            raw_ld = candidate_profile.raw_json_ld or {}
            same_as = raw_ld.get("sameAs") or []
            if isinstance(same_as, str):
                same_as = [same_as]
            profile_text_to_search.extend(same_as)
        elif isinstance(candidate_profile, dict):
            for k, v in candidate_profile.items():
                if isinstance(v, str):
                    profile_text_to_search.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            profile_text_to_search.extend(str(val) for val in item.values())
                        elif isinstance(item, str):
                            profile_text_to_search.append(item)

        combined_profile_text = " ".join(profile_text_to_search).lower()

        if target_domain and target_domain in combined_profile_text:
            return IdentityVerificationResult(
                is_auto_attach=True,
                identity_status="verified",
                retrieval_status="retrieved",
                reason=f"Profile explicitly links confirmed company domain ({target_domain})",
            )

        # 4. Check for Company Name Mentions
        company_clean = company_name.strip().lower()
        company_token_pattern = re.compile(rf"\b{re.escape(company_clean)}\b", re.I)

        # Negative checks for known homonym / unrelated entities
        # E.g. Mysa Smart Thermostats vs Mysa Fintech
        unrelated_signals = [
            "thermostat", "smart home", "climate control", "electric baseboard",
            "in-floor", "hvac", "heating", "bb-v2",
        ] if company_clean == "mysa" else []

        is_unrelated_industry = any(sig in combined_profile_text for sig in unrelated_signals)
        if is_unrelated_industry:
            return IdentityVerificationResult(
                is_auto_attach=False,
                identity_status="unverified",
                retrieval_status="not_found",
                reason=f"Profile mentions '{company_name}' but references an unrelated entity/industry.",
            )

        if company_token_pattern.search(combined_profile_text):
            # Name + Company match WITHOUT domain verification or website confirmation
            # Strictly NEVER auto-attach; mark identity_unverified with likely match badge
            return IdentityVerificationResult(
                is_auto_attach=False,
                identity_status="likely_match",
                retrieval_status="identity_unverified",
                reason=f"Candidate mentions company name '{company_name}' but lacks domain or website confirmation. Requires user verification.",
            )

        # 5. Neither domain nor company name confirmed
        return IdentityVerificationResult(
            is_auto_attach=False,
            identity_status="unverified",
            retrieval_status="not_found",
            reason=f"Profile does not reference company '{company_name}' or domain '{company_domain}'.",
        )

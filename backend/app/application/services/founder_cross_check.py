"""Title normalization and cross-checking between website and LinkedIn profiles.

Rules:
1. Normalize titles before comparing:
   - CEO == Chief Executive Officer
   - CTO == Chief Technology Officer
   - COO == Chief Operating Officer
   - CPO == Chief Product Officer
   - CFO == Chief Financial Officer
   - Co-founder == Founder == Co-Founder == Co Founder
   - '&' == 'and'
   - Case-insensitive, strip punctuation.
2. Compare ONLY when LinkedIn current position is at this company.
3. Label results "Differences found - verify" (low severity).
4. Resistant to false positives from wording or phrasing variations.
"""
from __future__ import annotations

import re
from typing import Any

from app.domain.entities.discovery import CrossCheckConflict, ExperienceItem


class FounderCrossCheckService:
    """Performs semantic cross-checks between website evidence and LinkedIn profile data."""

    ROLE_ACRONYMS = {
        "ceo": "chief executive officer",
        "cto": "chief technology officer",
        "coo": "chief operating officer",
        "cpo": "chief product officer",
        "cfo": "chief financial officer",
        "cro": "chief revenue officer",
        "cmo": "chief marketing officer",
        "vp": "vice president",
        "svp": "senior vice president",
        "avp": "assistant vice president",
    }

    @classmethod
    def normalize_title_tokens(cls, title: str | None) -> set[str]:
        """Convert a title into a set of normalized semantic role tokens."""
        if not title:
            return set()

        text = title.lower()
        # Replace & with and
        text = re.sub(r"&", " and ", text)
        # Normalize co-founder variations to founder
        text = re.sub(r"\bco[- ]?founder\b", "founder", text)
        # Remove separators and punctuation
        text = re.sub(r"[/|·,;()\-]", " ", text)
        words = text.split()

        normalized_words: list[str] = []
        i = 0
        while i < len(words):
            w = words[i]
            # Replace acronyms
            if w in cls.ROLE_ACRONYMS:
                normalized_words.extend(cls.ROLE_ACRONYMS[w].split())
            else:
                normalized_words.append(w)
            i += 1

        rejoined = " ".join(normalized_words)

        # Detect semantic role concepts
        concepts: set[str] = set()
        if "chief executive officer" in rejoined:
            concepts.add("chief executive officer")
            rejoined = rejoined.replace("chief executive officer", "")
        if "chief technology officer" in rejoined:
            concepts.add("chief technology officer")
            rejoined = rejoined.replace("chief technology officer", "")
        if "chief operating officer" in rejoined:
            concepts.add("chief operating officer")
            rejoined = rejoined.replace("chief operating officer", "")
        if "chief product officer" in rejoined:
            concepts.add("chief product officer")
            rejoined = rejoined.replace("chief product officer", "")
        if "chief financial officer" in rejoined:
            concepts.add("chief financial officer")
            rejoined = rejoined.replace("chief financial officer", "")

        if "founder" in rejoined:
            concepts.add("founder")
            rejoined = rejoined.replace("founder", "")
        if "director" in rejoined:
            concepts.add("director")
            rejoined = rejoined.replace("director", "")
        if "advisor" in rejoined:
            concepts.add("advisor")
            rejoined = rejoined.replace("advisor", "")
        if "investor" in rejoined:
            concepts.add("investor")
            rejoined = rejoined.replace("investor", "")

        # Add remaining non-stop words
        for w in rejoined.split():
            if w not in ("and", "at", "the", "of", "in", "for"):
                concepts.add(w)

        return concepts

    @classmethod
    def _is_position_at_company(cls, company_field: str, target_company: str) -> bool:
        if not company_field or not target_company:
            return False
        clean_pos = re.sub(r"[^a-zA-Z0-9]", "", company_field.lower())
        clean_target = re.sub(r"[^a-zA-Z0-9]", "", target_company.lower())
        return clean_target in clean_pos or clean_pos in clean_target

    @classmethod
    def cross_check_founder_role(
        cls,
        founder_name: str,
        website_role: str | None,
        experiences: list[ExperienceItem] | list[dict[str, Any]],
        company_name: str,
    ) -> list[CrossCheckConflict]:
        """Cross-check founder role between website and current LinkedIn position at target company.

        Returns list of CrossCheckConflict (empty if roles match or no current position at company).
        """
        if not website_role:
            return []

        # Find current position at target company
        current_company_position: str | None = None
        for exp in experiences:
            exp_company = exp.company if isinstance(exp, ExperienceItem) else exp.get("company", "")
            exp_title = exp.title if isinstance(exp, ExperienceItem) else exp.get("title") or exp.get("role", "")
            is_current = exp.is_current if isinstance(exp, ExperienceItem) else (
                exp.get("is_current", False) or "present" in str(exp.get("end", "")).lower() or "present" in str(exp.get("duration", "")).lower()
            )

            if is_current and cls._is_position_at_company(exp_company, company_name):
                current_company_position = exp_title
                break

        # If LinkedIn has no current position at this company, rule specifies: DO NOT compare!
        if not current_company_position:
            return []

        web_tokens = cls.normalize_title_tokens(website_role)
        li_tokens = cls.normalize_title_tokens(current_company_position)

        if not web_tokens or not li_tokens:
            return []

        # Check for intersection / compatibility
        # If one is a subset of the other or they share core leadership roles, no conflict
        core_leadership = {
            "chief executive officer",
            "chief technology officer",
            "chief operating officer",
            "chief product officer",
            "chief financial officer",
        }

        web_core = web_tokens.intersection(core_leadership)
        li_core = li_tokens.intersection(core_leadership)

        # If both state a different core C-level role (e.g. CEO vs CTO)
        if web_core and li_core and web_core != li_core:
            return [
                CrossCheckConflict(
                    field_name="Title / Role",
                    website_value=website_role,
                    linkedin_value=current_company_position,
                    details=f"Differences found - verify: Website states '{website_role}' while LinkedIn current position lists '{current_company_position}'.",
                    severity="low",
                )
            ]

        # If one has "founder" and the other has a completely unrelated non-leadership title (e.g. Advisor, Consultant)
        non_leadership = {"advisor", "consultant", "intern"}
        if "founder" in web_tokens and li_tokens.intersection(non_leadership) and not li_tokens.intersection(core_leadership | {"founder"}):
            return [
                CrossCheckConflict(
                    field_name="Title / Role",
                    website_value=website_role,
                    linkedin_value=current_company_position,
                    details=f"Differences found - verify: Website states '{website_role}' while LinkedIn lists '{current_company_position}'.",
                    severity="low",
                )
            ]

        # Otherwise they are considered compatible phrasing
        return []

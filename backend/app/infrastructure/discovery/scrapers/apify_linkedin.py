"""Apify LinkedIn Profile Scraper implementing ProfileScraperPort.

Integrates the official Apify Actor 'harvestapi/linkedin-profile-scraper' using
the exact actor input schema:
- profileScraperMode: "Profile details no email ($4 per 1k)"
- queries: [url]

Performs pay-per-event ($4/1k profiles) extraction without requiring cookies or
browser logins, resolving bot protection challenges on datacenter IPs.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from apify_client import ApifyClientAsync

from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.domain.entities.discovery import CompanyProfile, PersonProfile, SourceDiagnostic

logger = logging.getLogger(__name__)

ACTOR_ID = "harvestapi/linkedin-profile-scraper"
DEFAULT_PROFILE_SCRAPER_MODE = "Profile details no email ($4 per 1k)"


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URLs for consistent queries."""
    if not url:
        return url
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    parsed = urlparse(cleaned)
    netloc = parsed.netloc.lower()
    if "linkedin.com" in netloc:
        netloc = "www.linkedin.com"
    clean_path = parsed.path.rstrip("/")
    return f"https://{netloc}{clean_path}"


def map_apify_item_to_person_profile(
    item: dict[str, Any],
    fallback_url: str,
    retrieved_at: str | None = None,
) -> PersonProfile:
    """Map raw item output from harvestapi/linkedin-profile-scraper to PersonProfile."""
    now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()

    first_name = str(item.get("firstName") or "").strip()
    last_name = str(item.get("lastName") or "").strip()
    if first_name and last_name:
        name: str | None = f"{first_name} {last_name}"
    elif first_name:
        name = first_name
    elif last_name:
        name = last_name
    else:
        name = str(item.get("name") or "").strip() or None

    headline = str(item.get("headline") or "").strip() or None
    summary = str(item.get("about") or item.get("summary") or "").strip() or None

    # Location resolution
    loc_raw = item.get("location")
    location: str | None = None
    if isinstance(loc_raw, dict):
        loc_text = loc_raw.get("linkedinText") or loc_raw.get("text")
        if not loc_text and isinstance(loc_raw.get("parsed"), dict):
            loc_text = loc_raw["parsed"].get("text")
        location = str(loc_text).strip() if loc_text else None
    elif isinstance(loc_raw, str) and loc_raw.strip():
        location = loc_raw.strip()

    avatar_url = str(item.get("photo") or item.get("avatar_url") or "").strip() or None

    # Followers / Connections
    follower_count: int | None = None
    fc = item.get("followerCount")
    if isinstance(fc, int):
        follower_count = fc
    elif isinstance(fc, str) and fc.isdigit():
        follower_count = int(fc)

    connection_count: int | None = None
    cc = item.get("connectionsCount")
    if isinstance(cc, int):
        connection_count = cc
    elif isinstance(cc, str) and cc.isdigit():
        connection_count = int(cc)

    # Experience
    experiences: list[dict[str, Any]] = []
    for exp in item.get("experience", []) or []:
        if not isinstance(exp, dict):
            continue
        pos = str(exp.get("position") or exp.get("title") or "").strip()
        comp = str(exp.get("companyName") or exp.get("company") or "").strip()
        dur = str(exp.get("duration") or "").strip()
        desc = str(exp.get("description") or "").strip()

        start_raw = exp.get("startDate")
        start_str = ""
        if isinstance(start_raw, dict):
            start_str = str(
                start_raw.get("text") or f"{start_raw.get('month', '')} {start_raw.get('year', '')}"
            ).strip()
        elif start_raw:
            start_str = str(start_raw).strip()

        end_raw = exp.get("endDate")
        end_str = ""
        if isinstance(end_raw, dict):
            end_str = str(
                end_raw.get("text") or f"{end_raw.get('month', '')} {end_raw.get('year', '')}"
            ).strip()
        elif end_raw:
            end_str = str(end_raw).strip()

        is_current = end_str.lower() in ("present", "current") or (not end_str and bool(start_str))

        experiences.append({
            "title": pos,
            "company": comp,
            "start": start_str,
            "end": end_str,
            "duration": dur,
            "description": desc,
            "is_current": is_current,
        })

    # Education
    education: list[dict[str, Any]] = []
    for ed in item.get("education", []) or []:
        if not isinstance(ed, dict):
            continue
        school = str(ed.get("schoolName") or ed.get("institution") or ed.get("school") or "").strip()
        deg = str(ed.get("degree") or ed.get("degreeName") or "").strip()
        field_study = str(ed.get("fieldOfStudy") or ed.get("field") or "").strip()

        s_date = ed.get("startDate")
        start_yr = ""
        if isinstance(s_date, dict):
            start_yr = str(s_date.get("year") or "").strip()
        elif s_date:
            start_yr = str(s_date).strip()

        e_date = ed.get("endDate")
        end_yr = ""
        if isinstance(e_date, dict):
            end_yr = str(e_date.get("year") or "").strip()
        elif e_date:
            end_yr = str(e_date).strip()

        yr = end_yr or start_yr

        education.append({
            "institution": school,
            "school": school,
            "degree": deg,
            "field": field_study,
            "year": yr,
            "start_year": start_yr,
            "end_year": end_yr,
        })

    # Skills
    skills: list[str] = []
    for s in item.get("skills", []) or []:
        s_name = ""
        if isinstance(s, dict) and s.get("name"):
            s_name = str(s["name"]).strip()
        elif isinstance(s, str) and s.strip():
            s_name = s.strip()
        if s_name and s_name not in skills:
            skills.append(s_name)

    if not skills and item.get("topSkills"):
        for ts in str(item["topSkills"]).split("•"):
            ts_clean = ts.strip()
            if ts_clean and ts_clean not in skills:
                skills.append(ts_clean)

    # Certifications
    certifications: list[str] = []
    for c in item.get("certifications", []) or []:
        if isinstance(c, dict) and c.get("title"):
            cert_title = str(c["title"]).strip()
            issuer = str(c.get("issuedBy") or "").strip()
            label = f"{cert_title} - {issuer}" if issuer else cert_title
            if label not in certifications:
                certifications.append(label)
        elif isinstance(c, str) and c.strip():
            c_str = c.strip()
            if c_str not in certifications:
                certifications.append(c_str)

    # Languages
    languages: list[str] = []
    for lang in item.get("languages", []) or []:
        if isinstance(lang, dict) and lang.get("name"):
            l_name = str(lang["name"]).strip()
            prof = str(lang.get("proficiency") or "").strip()
            l_label = f"{l_name} ({prof})" if prof else l_name
            if l_label not in languages:
                languages.append(l_label)
        elif isinstance(lang, str) and lang.strip():
            lang_str = lang.strip()
            if lang_str not in languages:
                languages.append(lang_str)

    target_url = str(item.get("linkedinUrl") or fallback_url)

    return PersonProfile(
        name=name,
        headline=headline,
        location=location,
        summary=summary,
        education=education,
        experience=experiences,
        follower_count=follower_count,
        connection_count=connection_count,
        avatar_url=avatar_url,
        url=target_url,
        retrieved_at=now_iso,
        is_auth_walled=False,
        raw_json_ld=item,
        skills=skills,
        certifications=certifications,
        languages=languages,
        identity_status="verified",
    )


class ApifyLinkedInScraper(ProfileScraperPort):
    """Profile scraper backed by Apify Actor harvestapi/linkedin-profile-scraper."""

    def __init__(
        self,
        token: str | None = None,
        client: ApifyClientAsync | None = None,
        actor_id: str = ACTOR_ID,
        profile_scraper_mode: str = DEFAULT_PROFILE_SCRAPER_MODE,
        fallback_scraper: ProfileScraperPort | None = None,
    ) -> None:
        self._token = token
        self._client = client
        self._actor_id = actor_id
        self._profile_scraper_mode = profile_scraper_mode
        self._fallback_scraper = fallback_scraper

    def _get_client(self) -> ApifyClientAsync:
        if self._client is not None:
            return self._client
        if not self._token:
            raise ValueError("APIFY_TOKEN is required to initialize ApifyClient.")
        return ApifyClientAsync(token=self._token)

    async def fetch_company(self, url: str) -> CompanyProfile | None:
        """Fetch company profile. Delegates to fallback scraper if configured."""
        if self._fallback_scraper:
            return await self._fallback_scraper.fetch_company(url)
        return None

    async def fetch_company_with_diagnostic(
        self, url: str
    ) -> tuple[CompanyProfile | None, SourceDiagnostic]:
        """Fetch company profile with diagnostics."""
        if self._fallback_scraper:
            return await self._fallback_scraper.fetch_company_with_diagnostic(url)
        return None, SourceDiagnostic(
            url=url,
            outcome="not_supported",
            bytes_fetched=0,
            fields_extracted=[],
            error_details="harvestapi/linkedin-profile-scraper is configured for personal profiles.",
        )

    async def fetch_person(self, url: str) -> PersonProfile | None:
        """Fetch person profile. Returns None if unretrievable."""
        profile, _ = await self.fetch_person_with_diagnostic(url)
        return profile

    async def fetch_person_with_diagnostic(
        self, url: str
    ) -> tuple[PersonProfile | None, SourceDiagnostic]:
        """Fetch and parse LinkedIn person profile via Apify Actor."""
        normalized_url = normalize_linkedin_url(url)

        # Check token availability
        if not self._token and self._client is None:
            if self._fallback_scraper:
                logger.info("APIFY_TOKEN not configured; delegating to fallback scraper for '%s'", url)
                return await self._fallback_scraper.fetch_person_with_diagnostic(normalized_url)
            return None, SourceDiagnostic(
                url=normalized_url,
                outcome="token_missing",
                bytes_fetched=0,
                fields_extracted=[],
                error_details="Apify scraping skipped: APIFY_TOKEN is not configured.",
            )

        client = self._get_client()

        # Exact schema required by harvestapi/linkedin-profile-scraper
        run_input: dict[str, Any] = {
            "profileScraperMode": self._profile_scraper_mode,
            "queries": [normalized_url],
        }

        try:
            logger.info("Starting Apify Actor '%s' for URL: %s", self._actor_id, normalized_url)
            run = await client.actor(self._actor_id).call(run_input=run_input)
            if not run:
                raise RuntimeError("Apify Actor call returned None (timed out or aborted).")

            # Extract dataset ID (handle model attribute or dict)
            dataset_id = getattr(run, "default_dataset_id", None)
            if not dataset_id and isinstance(run, dict):
                dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
            if not dataset_id:
                raise RuntimeError("Apify Actor run did not provide a default dataset ID.")

            dataset_page = await client.dataset(dataset_id).list_items()
            items: list[dict[str, Any]] = []
            if hasattr(dataset_page, "items") and isinstance(dataset_page.items, list):
                items = dataset_page.items
            elif isinstance(dataset_page, list):
                items = dataset_page
            elif isinstance(dataset_page, dict) and "items" in dataset_page:
                items = dataset_page["items"]

            if not items:
                logger.warning("Apify Actor returned empty dataset for '%s'", normalized_url)
                return None, SourceDiagnostic(
                    url=normalized_url,
                    outcome="not_found",
                    bytes_fetched=0,
                    fields_extracted=[],
                    error_details="No profile data returned by Apify Actor for the given URL.",
                )

            item = items[0]
            status_code = item.get("status")
            if status_code in (404, 410):
                return None, SourceDiagnostic(
                    url=normalized_url,
                    outcome="not_found",
                    bytes_fetched=0,
                    fields_extracted=[],
                    error_details=f"Apify reported profile status {status_code}.",
                )

            profile = map_apify_item_to_person_profile(item, fallback_url=normalized_url)

            fields: list[str] = []
            if profile.name:
                fields.append("name")
            if profile.headline:
                fields.append("headline")
            if profile.summary:
                fields.append("summary")
            if profile.location:
                fields.append("location")
            if profile.experience:
                fields.append("experience")
            if profile.education:
                fields.append("education")
            if profile.skills:
                fields.append("skills")
            if profile.certifications:
                fields.append("certifications")
            if profile.languages:
                fields.append("languages")

            raw_bytes = len(json.dumps(item).encode("utf-8"))
            outcome = "ok" if fields else "empty_text"

            return profile, SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=raw_bytes,
                fields_extracted=fields,
                error_details=None,
            )

        except Exception as exc:
            logger.warning("Apify actor execution failed for '%s': %s", normalized_url, exc)

            status_code = getattr(exc, "status_code", None)
            if not status_code and hasattr(exc, "response"):
                status_code = getattr(exc.response, "status_code", None)

            err_text = str(exc)
            err_lower = err_text.lower()
            outcome = "apify_error"
            if status_code == 401 or "unauthorized" in err_lower or "token" in err_lower:
                outcome = "apify_unauthorized"
            elif status_code == 429 or "rate limit" in err_lower:
                outcome = "apify_rate_limited"
            elif status_code in (402, 403) or "credit" in err_lower or "payment" in err_lower:
                outcome = "apify_payment_required"

            # If fallback scraper is present, attempt fallback
            if self._fallback_scraper:
                logger.info(
                    "Attempting fallback scraper for '%s' following Apify failure (%s)",
                    normalized_url,
                    outcome,
                )
                return await self._fallback_scraper.fetch_person_with_diagnostic(normalized_url)

            return None, SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=0,
                fields_extracted=[],
                error_details=f"Apify execution failed: {err_text}",
            )

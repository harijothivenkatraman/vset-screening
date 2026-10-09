"""Bright Data LinkedIn Scraper implementing ProfileScraperPort.

Integrates Bright Data's managed LinkedIn Scraper API via brightdata-sdk,
handling proxy rotation, anti-bot challenges, and structured extraction.
Supports both personal profiles and company profiles.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from brightdata import BrightDataClient

from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.domain.entities.discovery import CompanyProfile, PersonProfile, SourceDiagnostic

logger = logging.getLogger(__name__)


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


def map_brightdata_item_to_person_profile(
    item: dict[str, Any],
    fallback_url: str,
    retrieved_at: str | None = None,
) -> PersonProfile:
    """Map raw Bright Data LinkedIn profile output to PersonProfile."""
    now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()

    name = str(item.get("name") or "").strip()
    if not name:
        first = str(item.get("first_name") or item.get("firstName") or "").strip()
        last = str(item.get("last_name") or item.get("lastName") or "").strip()
        if first and last:
            name = f"{first} {last}"
        elif first or last:
            name = first or last
    name_clean = name or None

    headline = str(
        item.get("headline")
        or item.get("position")
        or item.get("title")
        or (
            item.get("current_company", {}).get("title")
            if isinstance(item.get("current_company"), dict)
            else ""
        )
        or ""
    ).strip() or None
    summary = str(
        item.get("about") or item.get("summary") or item.get("description") or ""
    ).strip() or None

    # Location
    loc = item.get("location")
    location_clean: str | None = None
    if isinstance(loc, dict):
        loc_text = loc.get("text") or loc.get("city") or loc.get("country")
        location_clean = str(loc_text).strip() if loc_text else None
    elif isinstance(loc, str) and loc.strip():
        location_clean = loc.strip()
    elif item.get("city") or item.get("country"):
        parts = [str(item.get("city") or "").strip(), str(item.get("country") or "").strip()]
        location_clean = ", ".join(p for p in parts if p) or None

    avatar_url = str(
        item.get("avatar")
        or item.get("profile_image")
        or item.get("photo")
        or item.get("picture")
        or ""
    ).strip() or None

    fc = item.get("followers") or item.get("followers_count") or item.get("followerCount")
    follower_count = int(fc) if isinstance(fc, (int, str)) and str(fc).isdigit() else None

    cc = item.get("connections") or item.get("connections_count") or item.get("connectionsCount")
    connection_count = int(cc) if isinstance(cc, (int, str)) and str(cc).isdigit() else None

    # Experience
    raw_exp = item.get("experience") or item.get("work_experience") or []
    experiences: list[dict[str, Any]] = []
    if isinstance(raw_exp, list):
        for exp in raw_exp:
            if not isinstance(exp, dict):
                continue
            comp = str(
                exp.get("company") or exp.get("company_name") or exp.get("companyName") or ""
            ).strip()

            # Check for nested positions within a company group (e.g. Sundar Pichai at Google)
            sub_positions = exp.get("positions")
            if isinstance(sub_positions, list) and len(sub_positions) > 0:
                for sub in sub_positions:
                    if not isinstance(sub, dict):
                        continue
                    sub_title = str(sub.get("title") or sub.get("position") or "").strip()
                    sub_comp = str(sub.get("subtitle") or comp).strip()
                    sub_desc = str(sub.get("description") or sub.get("info") or "").strip()
                    sub_dur = str(sub.get("duration") or sub.get("meta") or "").strip()
                    sub_start = str(
                        sub.get("start_date") or sub.get("startDate") or sub.get("start") or ""
                    ).strip()
                    sub_end = str(
                        sub.get("end_date") or sub.get("endDate") or sub.get("end") or ""
                    ).strip()

                    # Infer start/end from duration/meta if explicit dates are blank
                    if not sub_start and sub_dur and " - " in sub_dur:
                        parts = sub_dur.split(" - ")
                        sub_start = parts[0].strip()
                        if len(parts) > 1:
                            sub_end = parts[1].split()[0].strip()

                    sub_is_curr = bool(
                        sub.get("is_current")
                        or (sub_end and sub_end.lower() in ("present", "current"))
                        or ("present" in sub_dur.lower())
                    )

                    experiences.append({
                        "title": sub_title or comp,
                        "company": sub_comp or comp,
                        "start": sub_start,
                        "end": sub_end,
                        "duration": sub_dur,
                        "description": sub_desc,
                        "is_current": sub_is_curr,
                    })
            else:
                pos = str(exp.get("title") or exp.get("position") or "").strip()
                desc = str(exp.get("description") or exp.get("info") or "").strip()
                dur = str(exp.get("duration") or exp.get("meta") or "").strip()
                start_str = str(
                    exp.get("start_date") or exp.get("startDate") or exp.get("start") or ""
                ).strip()
                end_str = str(
                    exp.get("end_date") or exp.get("endDate") or exp.get("end") or ""
                ).strip()

                if not start_str and dur and " - " in dur:
                    parts = dur.split(" - ")
                    start_str = parts[0].strip()
                    if len(parts) > 1:
                        end_str = parts[1].split()[0].strip()

                is_curr = bool(
                    exp.get("is_current")
                    or (end_str and end_str.lower() in ("present", "current"))
                    or (not end_str and bool(start_str))
                    or ("present" in dur.lower())
                )

                experiences.append({
                    "title": pos or comp,
                    "company": comp,
                    "start": start_str,
                    "end": end_str,
                    "duration": dur,
                    "description": desc,
                    "is_current": is_curr,
                })

    # If experiences list is empty, fallback to current_company metadata
    curr_comp = item.get("current_company")
    if not experiences and isinstance(curr_comp, dict) and curr_comp.get("name"):
        comp_name = str(curr_comp.get("name") or "").strip()
        comp_title = str(curr_comp.get("title") or headline or "Founder").strip()
        experiences.append({
            "title": comp_title,
            "company": comp_name,
            "start": "",
            "end": "Present",
            "duration": "",
            "description": "",
            "is_current": True,
        })

    # Education
    raw_edu = item.get("education") or []
    education: list[dict[str, Any]] = []
    if isinstance(raw_edu, list):
        for ed in raw_edu:
            if not isinstance(ed, dict):
                continue
            school = str(
                ed.get("school")
                or ed.get("school_name")
                or ed.get("institution")
                or ed.get("title")
                or ed.get("name")
                or item.get("educations_details")
                or ""
            ).strip()
            deg = str(
                ed.get("degree")
                or ed.get("degree_name")
                or ed.get("subtitle")
                or ""
            ).strip()
            field_study = str(ed.get("field_of_study") or ed.get("field") or "").strip()
            start_yr = str(ed.get("start_year") or ed.get("start_date") or "").strip()
            end_yr = str(ed.get("end_year") or ed.get("end_date") or "").strip()
            yr = end_yr or start_yr
            education.append({
                "institution": school,
                "school": school,
                "degree": deg,
                "field": field_study,
                "year": yr,
                "start_year": start_yr,
                "end_year": end_yr,
                "description": str(ed.get("description") or "").strip(),
            })

    # Skills
    raw_skills = item.get("skills") or item.get("top_skills") or []
    skills: list[str] = []
    if isinstance(raw_skills, list):
        for s in raw_skills:
            s_name = ""
            if isinstance(s, dict) and s.get("name"):
                s_name = str(s["name"]).strip()
            elif isinstance(s, str) and s.strip():
                s_name = s.strip()
            if s_name and s_name not in skills:
                skills.append(s_name)

    # Certifications
    raw_certs = item.get("certifications") or item.get("licenses_and_certifications") or []
    certifications: list[str] = []
    if isinstance(raw_certs, list):
        for c in raw_certs:
            if isinstance(c, dict) and (c.get("name") or c.get("title")):
                t = str(c.get("name") or c.get("title")).strip()
                iss = str(c.get("issuer") or c.get("issued_by") or c.get("subtitle") or "").strip()
                label = f"{t} - {iss}" if iss and iss.strip().lower() != t.strip().lower() else t
                if label not in certifications:
                    certifications.append(label)
            elif isinstance(c, str) and c.strip():
                c_str = c.strip()
                if c_str not in certifications:
                    certifications.append(c_str)

    # Languages
    raw_langs = item.get("languages") or []
    languages: list[str] = []
    if isinstance(raw_langs, list):
        for l in raw_langs:
            if isinstance(l, dict) and l.get("name"):
                n = str(l["name"]).strip()
                p = str(l.get("proficiency") or "").strip()
                label = f"{n} ({p})" if p else n
                if label not in languages:
                    languages.append(label)
            elif isinstance(l, str) and l.strip():
                l_str = l.strip()
                if l_str not in languages:
                    languages.append(l_str)

    # Honors & Awards
    raw_honors = item.get("honors_and_awards") or item.get("honors") or item.get("awards") or []
    honors_and_awards: list[dict[str, Any]] = []
    if isinstance(raw_honors, list):
        for h in raw_honors:
            if isinstance(h, dict):
                h_title = str(h.get("title") or h.get("name") or "").strip()
                h_pub = str(h.get("publication") or h.get("issuer") or h.get("issuer_name") or "").strip()
                h_date = str(h.get("date") or h.get("issue_date") or "").strip()
                if h_date and "T" in h_date:
                    h_date = h_date.split("T")[0]
                h_desc = str(h.get("description") or "").strip()
                if h_title:
                    honors_and_awards.append({
                        "title": h_title,
                        "issuer": h_pub,
                        "date": h_date,
                        "description": h_desc,
                    })
            elif isinstance(h, str) and h.strip():
                honors_and_awards.append({"title": h.strip(), "issuer": "", "date": "", "description": ""})

    # Publications
    raw_pubs = item.get("publications") or []
    publications: list[dict[str, Any]] = []
    if isinstance(raw_pubs, list):
        for p in raw_pubs:
            if isinstance(p, dict):
                p_title = str(p.get("title") or p.get("name") or "").strip()
                p_sub = str(p.get("subtitle") or p.get("publisher") or "").strip()
                p_date = str(p.get("date") or "").strip()
                p_desc = str(p.get("description") or "").strip()
                p_url = str(p.get("url") or p.get("link") or "").strip()
                if p_title:
                    publications.append({
                        "title": p_title,
                        "publisher": p_sub,
                        "date": p_date,
                        "description": p_desc,
                        "url": p_url,
                    })
            elif isinstance(p, str) and p.strip():
                publications.append({"title": p.strip(), "publisher": "", "date": "", "description": "", "url": ""})

    # Volunteer Experience
    raw_vol = item.get("volunteer_experience") or item.get("volunteering") or []
    volunteer_experience: list[dict[str, Any]] = []
    if isinstance(raw_vol, list):
        for v in raw_vol:
            if isinstance(v, dict):
                v_title = str(v.get("title") or v.get("role") or "").strip()
                v_sub = str(v.get("subtitle") or v.get("organization") or v.get("company") or "").strip()
                v_cause = str(v.get("cause") or "").strip()
                v_dur = str(v.get("duration") or v.get("duration_short") or "").strip()
                v_desc = str(v.get("info") or v.get("description") or "").strip()
                if v_title or v_sub:
                    volunteer_experience.append({
                        "role": v_title,
                        "organization": v_sub,
                        "cause": v_cause,
                        "duration": v_dur,
                        "description": v_desc,
                    })
            elif isinstance(v, str) and v.strip():
                volunteer_experience.append({"role": v.strip(), "organization": "", "cause": "", "duration": "", "description": ""})

    # Courses
    raw_courses = item.get("courses") or []
    courses: list[dict[str, Any]] = []
    if isinstance(raw_courses, list):
        for crs in raw_courses:
            if isinstance(crs, dict):
                c_name = str(crs.get("name") or crs.get("title") or "").strip()
                c_num = str(crs.get("number") or "").strip()
                if c_name:
                    courses.append({"name": c_name, "number": c_num})
            elif isinstance(crs, str) and crs.strip():
                courses.append({"name": crs.strip(), "number": ""})

    # Projects
    raw_proj = item.get("projects") or []
    projects: list[dict[str, Any]] = []
    if isinstance(raw_proj, list):
        for pr in raw_proj:
            if isinstance(pr, dict):
                pr_title = str(pr.get("title") or pr.get("name") or "").strip()
                pr_desc = str(pr.get("description") or "").strip()
                pr_url = str(pr.get("url") or "").strip()
                if pr_title:
                    projects.append({"title": pr_title, "description": pr_desc, "url": pr_url})
            elif isinstance(pr, str) and pr.strip():
                projects.append({"title": pr.strip(), "description": "", "url": ""})

    # Recommendations
    raw_recs = item.get("recommendations") or []
    recommendations: list[str] = []
    if isinstance(raw_recs, list):
        for r in raw_recs:
            if isinstance(r, str) and r.strip():
                recommendations.append(r.strip())
            elif isinstance(r, dict) and r.get("text"):
                recommendations.append(str(r["text"]).strip())

    target_url = str(item.get("url") or item.get("link") or fallback_url)

    return PersonProfile(
        name=name_clean,
        headline=headline,
        location=location_clean,
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
        honors_and_awards=honors_and_awards,
        publications=publications,
        volunteer_experience=volunteer_experience,
        courses=courses,
        projects=projects,
        recommendations=recommendations,
        identity_status="verified",
    )


def map_brightdata_item_to_company_profile(
    item: dict[str, Any],
    fallback_url: str,
    retrieved_at: str | None = None,
) -> CompanyProfile:
    """Map raw Bright Data LinkedIn company output to CompanyProfile."""
    now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()
    return CompanyProfile(
        name=str(item.get("name") or "").strip() or None,
        description=str(item.get("about") or item.get("description") or "").strip() or None,
        industry=str(item.get("industry") or "").strip() or None,
        company_size=str(
            item.get("company_size") or item.get("employees_in_linkedin") or ""
        ).strip() or None,
        headquarters=str(item.get("headquarters") or item.get("city") or "").strip() or None,
        website=str(item.get("website") or item.get("link") or "").strip() or None,
        founded_year=str(item.get("founded") or item.get("founded_year") or "").strip() or None,
        specialties=list(item.get("specialties") or []),
        followers=int(item.get("followers") or item.get("followers_count") or 0) or None,
        logo_url=str(item.get("logo") or item.get("logo_url") or "").strip() or None,
        tagline=str(item.get("tagline") or "").strip() or None,
        url=str(item.get("url") or item.get("link") or fallback_url),
        retrieved_at=now_iso,
        is_auth_walled=False,
        raw_json_ld=item,
    )


class BrightDataLinkedInScraper(ProfileScraperPort):
    """Profile scraper backed by Bright Data's LinkedIn Scraper API."""

    def __init__(
        self,
        token: str | None = None,
        client: Any = None,
        timeout: int = 180,
    ) -> None:
        self._token = token
        self._client = client
        self._timeout = timeout

    async def fetch_company(self, url: str) -> CompanyProfile | None:
        """Fetch company profile."""
        profile, _ = await self.fetch_company_with_diagnostic(url)
        return profile

    async def fetch_company_with_diagnostic(
        self, url: str
    ) -> tuple[CompanyProfile | None, SourceDiagnostic]:
        """Fetch company profile with diagnostics."""
        normalized_url = normalize_linkedin_url(url)

        if not self._token and self._client is None:
            return None, SourceDiagnostic(
                url=normalized_url,
                outcome="token_missing",
                bytes_fetched=0,
                fields_extracted=[],
                error_details="Bright Data company scraping skipped: token not configured.",
            )

        try:
            logger.info("Starting Bright Data company scraper for: %s", normalized_url)
            if self._client is not None:
                res = await self._client.scrape.linkedin.companies(
                    url=normalized_url, timeout=self._timeout
                )
            else:
                async with BrightDataClient(
                    token=self._token, timeout=self._timeout, auto_create_zones=False
                ) as client:
                    res = await client.scrape.linkedin.companies(
                        url=normalized_url, timeout=self._timeout
                    )

            result_item = res[0] if isinstance(res, list) and res else res
            data = getattr(result_item, "data", None) if result_item else None
            if not data:
                return None, SourceDiagnostic(
                    url=normalized_url,
                    outcome="not_found",
                    bytes_fetched=0,
                    fields_extracted=[],
                    error_details="No company data returned by Bright Data.",
                )

            item = data[0] if isinstance(data, list) and data else data
            if not isinstance(item, dict):
                item = {}

            profile = map_brightdata_item_to_company_profile(item, fallback_url=normalized_url)
            fields = [
                k for k in ("name", "description", "industry", "headquarters", "website", "founded_year")
                if getattr(profile, k, None)
            ]
            raw_bytes = len(json.dumps(item).encode("utf-8"))
            outcome = "ok" if fields else "empty_text"
            return profile, SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=raw_bytes,
                fields_extracted=fields,
            )
        except Exception as exc:
            logger.warning("Bright Data company scrape failed for '%s': %s", normalized_url, exc)
            return None, SourceDiagnostic(
                url=normalized_url,
                outcome="brightdata_error",
                bytes_fetched=0,
                fields_extracted=[],
                error_details=f"Bright Data scrape failed: {exc}",
            )

    async def fetch_person(self, url: str) -> PersonProfile | None:
        """Fetch person profile."""
        profile, _ = await self.fetch_person_with_diagnostic(url)
        return profile

    async def fetch_person_with_diagnostic(
        self, url: str
    ) -> tuple[PersonProfile | None, SourceDiagnostic]:
        """Fetch and parse LinkedIn person profile via Bright Data."""
        normalized_url = normalize_linkedin_url(url)

        if not self._token and self._client is None:
            return None, SourceDiagnostic(
                url=normalized_url,
                outcome="token_missing",
                bytes_fetched=0,
                fields_extracted=[],
                error_details="Bright Data scraping skipped: BRIGHTDATA_API_TOKEN is not configured.",
            )

        try:
            logger.info("Starting Bright Data profile scraper for: %s", normalized_url)
            if self._client is not None:
                res = await self._client.scrape.linkedin.profiles(
                    url=normalized_url, timeout=self._timeout
                )
            else:
                async with BrightDataClient(
                    token=self._token, timeout=self._timeout, auto_create_zones=False
                ) as client:
                    res = await client.scrape.linkedin.profiles(
                        url=normalized_url, timeout=self._timeout
                    )

            result_item = res[0] if isinstance(res, list) and res else res
            data = getattr(result_item, "data", None) if result_item else None
            if not data:
                logger.warning("Bright Data returned no data for '%s'", normalized_url)
                return None, SourceDiagnostic(
                    url=normalized_url,
                    outcome="not_found",
                    bytes_fetched=0,
                    fields_extracted=[],
                    error_details="No profile data returned by Bright Data.",
                )

            item = data[0] if isinstance(data, list) and data else data
            if not isinstance(item, dict):
                item = {}

            profile = map_brightdata_item_to_person_profile(item, fallback_url=normalized_url)

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
            if profile.honors_and_awards:
                fields.append("honors_and_awards")
            if profile.publications:
                fields.append("publications")
            if profile.volunteer_experience:
                fields.append("volunteer_experience")
            if profile.courses:
                fields.append("courses")
            if profile.projects:
                fields.append("projects")
            if profile.recommendations:
                fields.append("recommendations")

            raw_bytes = len(json.dumps(item).encode("utf-8"))
            outcome = "ok" if fields else "empty_text"

            return profile, SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=raw_bytes,
                fields_extracted=fields,
            )

        except Exception as exc:
            logger.warning("Bright Data profile scrape failed for '%s': %s", normalized_url, exc)
            return None, SourceDiagnostic(
                url=normalized_url,
                outcome="brightdata_error",
                bytes_fetched=0,
                fields_extracted=[],
                error_details=f"Bright Data scrape failed: {exc}",
            )

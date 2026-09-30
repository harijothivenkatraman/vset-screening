import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.company import Company
from app.domain.entities.report import Report


def generate_slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    return re.sub(r"[\s-]+", "-", cleaned)


def parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def map_company_from_raw(raw_data: dict[str, Any], existing_id: UUID | None = None) -> Company:
    meta = raw_data.get("canonical", {}).get("meta", {})
    company_name = meta.get("company_name") or raw_data.get("meta", {}).get("company_name", "Unknown")
    website = meta.get("website") or raw_data.get("meta", {}).get("website")
    slug = generate_slug(company_name)

    now = datetime.now(timezone.utc)
    return Company(
        id=existing_id or uuid4(),
        slug=slug,
        name=company_name,
        website=website,
        created_at=now,
        updated_at=now,
    )


def map_report_from_raw(raw_data: dict[str, Any], company_id: UUID, existing_id: UUID | None = None) -> Report:
    canonical = raw_data.get("canonical", {})
    canonical_meta = canonical.get("meta", {})
    content = canonical.get("content", {})
    final = content.get("final", {})
    final_meta = final.get("meta", {})
    top_meta = raw_data.get("meta", {})
    presentation = raw_data.get("presentation", {})

    canonical_screen_id = canonical_meta.get("canonical_screen_id", "")
    report_id = canonical_meta.get("report_id")
    final_fingerprint = canonical_meta.get("final_fingerprint") or final_meta.get("final_fingerprint", "")
    audience = top_meta.get("audience", "FOUNDER")
    audience_label = presentation.get("audience_label", "Founder Screen")
    version = canonical_meta.get("version", "V1")
    canonical_version = canonical_meta.get("canonical_version", "")
    schema_version = final_meta.get("schema_version", "")
    research_cutoff = canonical_meta.get("research_cutoff")
    as_of_date = final_meta.get("as_of_date")
    generated_at = parse_datetime(canonical_meta.get("generated_at"))

    cover = content.get("cover", {})
    sections = content.get("sections", [])
    ribbon = sections[0].get("ribbon", []) if sections else []
    report_basis = final.get("report_basis", {})
    concerns_conflicts = final.get("concerns_conflicts", {})

    now = datetime.now(timezone.utc)
    return Report(
        id=existing_id or uuid4(),
        company_id=company_id,
        canonical_screen_id=canonical_screen_id,
        report_id=report_id,
        final_fingerprint=final_fingerprint,
        audience=audience,
        audience_label=audience_label,
        version=version,
        canonical_version=canonical_version,
        schema_version=schema_version,
        research_cutoff=research_cutoff,
        as_of_date=as_of_date,
        generated_at=generated_at,
        cover=cover,
        ribbon=ribbon,
        presentation=presentation,
        report_basis=report_basis,
        concerns_conflicts=concerns_conflicts,
        created_at=now,
        updated_at=now,
    )

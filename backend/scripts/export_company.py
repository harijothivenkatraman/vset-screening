#!/usr/bin/env python3
"""Export a company's screening report as sanitized canonical JSON.

Use this script to export screening data (e.g. fetched from a residential IP or local benchmark)
for durable import into a production environment (such as AWS Lightsail).

Exported files are guaranteed to be sanitized:
- No raw profile text, personal emails, phone numbers, or photo URLs
- Preserves all canonical facts, dates, amounts, rounds, and audit fingerprints

Usage:
  python scripts/export_company.py --slug mysa --output mysa_canonical.json

Importing into production:
  1. Via HTTP API (standard path):
     curl -X POST http://<LIGHTSAIL_IP>/api/v1/reports/import \\
       -H "X-API-Key: <IMPORT_API_KEY>" \\
       -H "Content-Type: application/json" \\
       --data-binary @mysa_canonical.json

  2. Via Python CLI on the instance:
     python -m app.scripts.import_report --file mysa_canonical.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.infrastructure.persistence.database import async_session_factory
from app.infrastructure.persistence.company_repo import SqlAlchemyCompanyRepository
from app.infrastructure.persistence.report_repo import SqlAlchemyReportRepository, sanitize_audit_snapshot

__all__ = ["main", "export_company"]




async def export_company(slug: str, output_path: str) -> None:
    async with async_session_factory() as session:
        company_repo = SqlAlchemyCompanyRepository(session)
        report_repo = SqlAlchemyReportRepository(session)

        company = await company_repo.find_by_slug(slug)
        if not company:
            print(f"Error: Company with slug '{slug}' not found in database.", file=sys.stderr)
            sys.exit(1)

        report = await report_repo.find_by_company_id(company.id)
        if not report:
            print(f"Error: No report found for company '{slug}' (ID: {company.id}).", file=sys.stderr)
            sys.exit(1)

        raw_snapshot = await report_repo.get_raw_snapshot(report.id)
        if not raw_snapshot:
            print(f"Error: No raw snapshot stored for report ID {report.id}.", file=sys.stderr)
            sys.exit(1)

        # Ensure deep sanitization before export
        clean_payload = sanitize_audit_snapshot(raw_snapshot)

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2, ensure_ascii=False)

        file_size_kb = out_file.stat().st_size / 1024
        print(f"Successfully exported sanitized canonical JSON for '{slug}' to {output_path} ({file_size_kb:.2f} KB).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a company screening report as sanitized canonical JSON for residential-to-production import.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--slug", required=True, help="Slug of the company to export (e.g. mysa, terraspark).")
    parser.add_argument("--output", "-o", default=None, help="Output JSON filepath (default: <slug>_canonical_export.json).")

    args = parser.parse_args()
    out_path = args.output or f"{args.slug}_canonical_export.json"

    asyncio.run(export_company(args.slug, out_path))


if __name__ == "__main__":
    main()

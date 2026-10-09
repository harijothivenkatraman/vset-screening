"""Extract four LinkedIn profiles using Bright Data API and render executive PDF reports.

Uses BrightDataLinkedInScraper adapter and ReportLab to generate publication-grade
B2B founder screening dossiers.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import get_settings
from app.domain.entities.discovery import PersonProfile, SourceDiagnostic
from app.infrastructure.discovery.scrapers.brightdata_linkedin import BrightDataLinkedInScraper


TARGET_PROFILES = [
    {
        "name": "Satya Nadella",
        "company": "Microsoft",
        "url": "https://www.linkedin.com/in/satyanadella",
        "filename": "Satya_Nadella_Founder_Profile.pdf",
    },
    {
        "name": "Reid Hoffman",
        "company": "LinkedIn / Greylock",
        "url": "https://www.linkedin.com/in/reidhoffman",
        "filename": "Reid_Hoffman_Founder_Profile.pdf",
    },
    {
        "name": "Sundar Pichai",
        "company": "Google / Alphabet",
        "url": "https://www.linkedin.com/in/sundarpichai",
        "filename": "Sundar_Pichai_Founder_Profile.pdf",
    },
    {
        "name": "Andrew Ng",
        "company": "Coursera / DeepLearning.AI",
        "url": "https://www.linkedin.com/in/andrewyng",
        "filename": "Andrew_Ng_Founder_Profile.pdf",
    },
]


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for total page count and professional running headers/footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(
                54,
                11 * inch - 36,
                "vSET Commercial Screen · Founder Profile Dossier (Bright Data Verified)",
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running footer
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(8.5 * inch - 54, 30, page_str)
        self.drawString(
            54,
            30,
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Source: Bright Data LinkedIn API",
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 42, 8.5 * inch - 54, 42)
        self.restoreState()


def build_profile_pdf(
    profile: PersonProfile,
    diag: SourceDiagnostic,
    target_info: dict[str, str],
    output_path: Path,
) -> None:
    """Build a publication-grade PDF report for a single founder profile."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles adhering to vSET design tokens
    primary_color = colors.HexColor("#0f172a")  # Slate 900
    brand_blue = colors.HexColor("#0284c7")     # Sky 600
    slate_sub = colors.HexColor("#475569")      # Slate 600
    bg_light = colors.HexColor("#f8fafc")       # Slate 50
    border_color = colors.HexColor("#e2e8f0")   # Slate 200

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=slate_sub,
    )

    meta_badge_style = ParagraphStyle(
        "MetaBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0369a1"),
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=5,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=body_style,
        textColor=slate_sub,
    )

    story = []

    # 1. Top Platform Header & Category Eyebrow
    eyebrow = (
        f'<font color="#0284c7"><b>vSET SCREENING PLATFORM</b></font>'
        f' &nbsp;·&nbsp; FOUNDER PROFILE DOSSIER'
        f' &nbsp;·&nbsp; <font color="#059669"><b>{profile.identity_status.upper()}</b></font>'
    )
    story.append(Paragraph(eyebrow, meta_badge_style))
    story.append(Spacer(1, 4))

    # 2. Founder Name & Headline
    display_name = profile.name or target_info["name"]
    story.append(Paragraph(display_name, title_style))
    story.append(Spacer(1, 3))

    headline_text = profile.headline or f"Executive at {target_info['company']}"
    story.append(Paragraph(headline_text, subtitle_style))
    story.append(Spacer(1, 6))

    # 3. Key Telemetry & Coordinates Table
    raw_url = profile.url or target_info.get("url", "")
    short_url = raw_url.replace("https://", "").replace("http://", "").rstrip("/")
    if "linkedin.com/in/" in short_url:
        short_url = "linkedin.com/in/" + short_url.split("linkedin.com/in/")[-1].split("?")[0]

    coords_data = [
        [
            Paragraph("<b>Company Focus:</b>", body_muted),
            Paragraph(target_info["company"], body_style),
            Paragraph("<b>Location:</b>", body_muted),
            Paragraph(profile.location or "Not specified", body_style),
        ],
        [
            Paragraph("<b>Public Profile:</b>", body_muted),
            Paragraph(f'<link href="{profile.url}"><font color="#0284c7">{short_url}</font></link>', body_style),
            Paragraph("<b>Followers:</b>", body_muted),
            Paragraph(f"{profile.follower_count:,}" if profile.follower_count else "Not public", body_style),
        ],
        [
            Paragraph("<b>Extraction Source:</b>", body_muted),
            Paragraph("Bright Data Managed LinkedIn Scraper API", body_style),
            Paragraph("<b>Payload Size:</b>", body_muted),
            Paragraph(f"{diag.bytes_fetched:,} bytes", body_style),
        ],
    ]
    coords_table = Table(coords_data, colWidths=[1.4 * inch, 2.3 * inch, 1.2 * inch, 2.1 * inch])
    coords_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(coords_table)
    story.append(Spacer(1, 8))

    # 4. Summary / Executive Bio
    if profile.summary:
        story.append(Paragraph("Executive Summary & About", section_heading))
        summary_p = Paragraph(profile.summary.replace("\n", "<br/>"), body_style)
        summary_table = Table([[summary_p]], colWidths=[7.0 * inch])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINELEFT", (0, 0), (0, -1), 3, brand_blue),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 8))

    # 5. Career & Experience Timeline
    story.append(Paragraph(f"Career Experience Timeline ({len(profile.experience)} roles recorded)", section_heading))
    if profile.experience:
        exp_table_data = [
            [
                Paragraph("<b>Role & Organization</b>", meta_badge_style),
                Paragraph("<b>Tenure / Duration</b>", meta_badge_style),
                Paragraph("<b>Details & Scope</b>", meta_badge_style),
            ]
        ]
        for exp in profile.experience:
            role_text = f"<b>{exp.get('title') or 'Leader'}</b><br/><font color='#0284c7'>{exp.get('company') or 'Organization'}</font>"
            start = exp.get("start") or ""
            end = exp.get("end") or ""
            tenure = f"{start} – {end}" if start or end else "Recorded"
            dur = exp.get("duration")
            if dur:
                tenure += f"<br/><font color='#64748b'>({dur})</font>"
            
            desc = exp.get("description") or "—"
            if len(desc) > 280:
                desc = desc[:280] + "..."
            
            exp_table_data.append([
                Paragraph(role_text, body_style),
                Paragraph(tenure, body_style),
                Paragraph(desc, body_style),
            ])

        exp_table = Table(exp_table_data, colWidths=[2.3 * inch, 1.7 * inch, 3.0 * inch])
        exp_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(exp_table)
    else:
        story.append(Paragraph("<i>No career timeline records extracted.</i>", body_muted))

    story.append(Spacer(1, 10))

    # 6. Academic Background / Education
    story.append(Paragraph(f"Academic Background ({len(profile.education)} institutions)", section_heading))
    if profile.education:
        edu_table_data = [
            [
                Paragraph("<b>Institution</b>", meta_badge_style),
                Paragraph("<b>Degree & Field</b>", meta_badge_style),
                Paragraph("<b>Years</b>", meta_badge_style),
            ]
        ]
        for edu in profile.education:
            school_name = edu.get("school") or edu.get("institution") or "University / Institution"
            deg = edu.get("degree") or ""
            field = edu.get("field") or ""
            deg_field = f"{deg}, {field}".strip(", ") if deg or field else "Degree Studies"
            sy = edu.get("start_year") or ""
            ey = edu.get("end_year") or ""
            yr_str = f"{sy} – {ey}".strip(" –") if sy or ey else "Completed"

            edu_table_data.append([
                Paragraph(f"<b>{school_name}</b>", body_style),
                Paragraph(deg_field, body_style),
                Paragraph(yr_str, body_style),
            ])

        edu_table = Table(edu_table_data, colWidths=[3.2 * inch, 2.6 * inch, 1.2 * inch])
        edu_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(edu_table)
    else:
        story.append(Paragraph("<i>No academic records extracted.</i>", body_muted))

    story.append(Spacer(1, 10))

    # 7. Honors & Awards
    if profile.honors_and_awards:
        story.append(Paragraph(f"Honors & Awards ({len(profile.honors_and_awards)} recorded)", section_heading))
        honors_data = [
            [
                Paragraph("<b>Honor / Recognition</b>", meta_badge_style),
                Paragraph("<b>Conferred By / Issuer</b>", meta_badge_style),
                Paragraph("<b>Date & Synopsis</b>", meta_badge_style),
            ]
        ]
        for h in profile.honors_and_awards:
            h_title = h.get("title") or "Honor"
            h_issuer = h.get("issuer") or "—"
            h_date = h.get("date") or ""
            h_desc = h.get("description") or ""
            date_synopsis = f"<b>{h_date}</b>" if h_date else ""
            if h_desc:
                if len(h_desc) > 220:
                    h_desc = h_desc[:220] + "..."
                date_synopsis = f"{date_synopsis}<br/>{h_desc}" if date_synopsis else h_desc
            honors_data.append([
                Paragraph(f"<b>{h_title}</b>", body_style),
                Paragraph(h_issuer, body_style),
                Paragraph(date_synopsis or "Conferred", body_style),
            ])
        honors_table = Table(honors_data, colWidths=[2.5 * inch, 1.9 * inch, 2.6 * inch])
        honors_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(honors_table)
        story.append(Spacer(1, 10))

    # 8. Publications & Authored Works
    if profile.publications:
        story.append(Paragraph(f"Publications & Authored Works ({len(profile.publications)} recorded)", section_heading))
        pubs_data = [
            [
                Paragraph("<b>Title / Work</b>", meta_badge_style),
                Paragraph("<b>Publisher / Outlet</b>", meta_badge_style),
                Paragraph("<b>Date & Synopsis</b>", meta_badge_style),
            ]
        ]
        for p in profile.publications:
            p_title = p.get("title") or "Publication"
            p_pub = p.get("publisher") or "—"
            p_date = p.get("date") or ""
            p_desc = p.get("description") or ""
            date_synopsis = f"<b>{p_date}</b>" if p_date else ""
            if p_desc:
                if len(p_desc) > 220:
                    p_desc = p_desc[:220] + "..."
                date_synopsis = f"{date_synopsis}<br/>{p_desc}" if date_synopsis else p_desc
            pubs_data.append([
                Paragraph(f"<b>{p_title}</b>", body_style),
                Paragraph(p_pub, body_style),
                Paragraph(date_synopsis or "Published", body_style),
            ])
        pubs_table = Table(pubs_data, colWidths=[2.5 * inch, 1.9 * inch, 2.6 * inch])
        pubs_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(pubs_table)
        story.append(Spacer(1, 10))

    # 9. Board Memberships & Community Leadership
    if profile.volunteer_experience:
        story.append(Paragraph(f"Board Memberships & Community Leadership ({len(profile.volunteer_experience)} recorded)", section_heading))
        vol_data = [
            [
                Paragraph("<b>Role & Organization</b>", meta_badge_style),
                Paragraph("<b>Cause / Domain</b>", meta_badge_style),
                Paragraph("<b>Tenure & Mission</b>", meta_badge_style),
            ]
        ]
        for v in profile.volunteer_experience[:8]:
            v_role = v.get("role") or "Member"
            v_org = v.get("organization") or "Organization"
            v_cause = v.get("cause") or "Leadership"
            v_dur = v.get("duration") or ""
            v_desc = v.get("description") or ""
            if len(v_desc) > 200:
                v_desc = v_desc[:200] + "..."
            right_col = f"<b>{v_dur}</b><br/>{v_desc}" if v_dur else v_desc
            vol_data.append([
                Paragraph(f"<b>{v_role}</b><br/><font color='#0284c7'>{v_org}</font>", body_style),
                Paragraph(v_cause, body_style),
                Paragraph(right_col or "Active", body_style),
            ])
        vol_table = Table(vol_data, colWidths=[2.5 * inch, 1.8 * inch, 2.7 * inch])
        vol_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(vol_table)
        story.append(Spacer(1, 10))

    # 10. Skills, Certifications & Languages
    misc_items = []
    if profile.skills:
        skill_str = " &nbsp;·&nbsp; ".join(f"<b>{s}</b>" for s in profile.skills[:15])
        misc_items.append((Paragraph("<b>Key Skills:</b>", body_bold), Paragraph(skill_str, body_style)))
    if profile.certifications:
        cert_str = "<br/>".join(f"• {c}" for c in profile.certifications[:8])
        misc_items.append((Paragraph("<b>Certifications:</b>", body_bold), Paragraph(cert_str, body_style)))
    if profile.languages:
        lang_str = ", ".join(profile.languages)
        misc_items.append((Paragraph("<b>Languages:</b>", body_bold), Paragraph(lang_str, body_style)))

    if misc_items:
        story.append(Paragraph("Competencies & Certifications", section_heading))
        misc_table = Table(misc_items, colWidths=[1.8 * inch, 5.2 * inch])
        misc_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(misc_table)

    # 11. Provenance & Verification Metadata Box
    story.append(Spacer(1, 8))
    provenance_text = (
        f"<b>Extraction & Audit Trail:</b> Mapped via Bright Data Managed LinkedIn Scraper API. "
        f"Diagnostic Outcome: <b>{diag.outcome.upper()}</b>. "
        f"Fields extracted: {', '.join(diag.fields_extracted)}. "
        f"Retrieved at: {profile.retrieved_at}."
    )
    prov_p = Paragraph(provenance_text, body_muted)
    prov_table = Table([[prov_p]], colWidths=[7.0 * inch])
    prov_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(prov_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)


async def main() -> None:
    settings = get_settings()
    token = settings.BRIGHTDATA_API_TOKEN
    if not token:
        print("ERROR: BRIGHTDATA_API_TOKEN is not configured!")
        sys.exit(1)

    print("=" * 70)
    print("EXTRACTING 4 FOUNDER PROFILES & GENERATING PDF DOSSIERS")
    print("=" * 70)
    print(f"API Token Active: True (Prefix: {token[:8]}...)")

    output_dir = PROJECT_ROOT / "output" / "profiles"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Artifact directory for antigravity Pair Programming assistant
    artifact_dir = Path(r"C:\Users\hari jothiveketraman\.gemini\antigravity-cli\brain\c45c4332-34ea-4e7d-a2ce-02e1eaaa9404")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scraper = BrightDataLinkedInScraper(token=token)

    results = []

    for idx, target in enumerate(TARGET_PROFILES, 1):
        print(f"\n[{idx}/4] Extracting LinkedIn Profile: {target['name']} ({target['company']})")
        print(f"      URL: {target['url']}")

        profile = None
        for attempt in range(2):
            profile, diag = await scraper.fetch_person_with_diagnostic(target["url"])
            if profile:
                break
            if attempt == 0:
                print(f"      Transient issue ({diag.outcome}: {diag.error_details}). Retrying in 3 seconds...")
                await asyncio.sleep(3)

        if not profile:
            print(f"      FAILED: Diagnostic outcome: {diag.outcome}, Error: {diag.error_details}")
            continue

        print(f"      Extraction Successful! (Outcome: {diag.outcome}, Bytes: {diag.bytes_fetched:,})")
        print(f"      Headline: {profile.headline}")
        print(f"      Experiences: {len(profile.experience)} (unpacked roles) | Education: {len(profile.education)}")
        print(f"      Honors: {len(profile.honors_and_awards)} | Pubs: {len(profile.publications)} | Volunteer: {len(profile.volunteer_experience)}")

        pdf_path = output_dir / target["filename"]
        print(f"      Rendering Executive PDF: {pdf_path.name}...")
        build_profile_pdf(profile, diag, target, pdf_path)
        print(f"      Saved: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")

        # Copy to artifact directory
        artifact_path = artifact_dir / target["filename"]
        shutil.copy2(pdf_path, artifact_path)
        print(f"      Artifact Copied: {artifact_path.name}")

        results.append({
            "target": target,
            "profile": profile,
            "diag": diag,
            "pdf_path": pdf_path,
            "size": pdf_path.stat().st_size,
        })

    print("\n" + "=" * 70)
    print("EXTRACTION & PDF GENERATION SUMMARY")
    print("=" * 70)
    for res in results:
        t = res["target"]
        p = res["profile"]
        print(f"[OK] {t['name']:<16} | {t['company']:<20} | PDF: {res['pdf_path'].name} ({res['size']:,} bytes)")
        print(f"     Exp: {len(p.experience)} | Edu: {len(p.education)} | Skills: {len(p.skills)} | Certs: {len(p.certifications)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

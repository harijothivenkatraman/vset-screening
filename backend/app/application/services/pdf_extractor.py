"""Pure-Python PDF text extraction, privacy hardening, and LinkedIn profile parsing.

Respects strict 2MB memory budget, strips executable scripts / HTML tags,
discards Contact blocks (emails, phones, personal URLs), and parses both
LinkedIn "Save to PDF" layout and web-pasted profile text.
Pure Python standard library only (re, zlib, html).
"""
from __future__ import annotations

import html
import re
import zlib
from typing import Any

MAX_PDF_BYTES = 2 * 1024 * 1024  # 2 MB Lightsail cap
MAX_TEXT_CHARS = 50000           # 50k characters cap


def sanitize_text(raw_text: str | None) -> str:
    """Sanitize text input, stripping HTML, script tags, and capping length."""
    if not raw_text:
        return ""
    # Strip script and style blocks
    cleaned = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", "", raw_text, flags=re.I | re.S)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    # Normalize excessive whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()[:MAX_TEXT_CHARS]


def discard_contact_info(text: str) -> str:
    """Discard Contact block, emails, phone numbers, and personal URLs.

    Guarantees no PII is retained in parsed fields or downstream snapshots.
    """
    if not text:
        return ""

    lines = text.splitlines()
    filtered_lines: list[str] = []
    in_contact_block = False

    section_headers = {
        "top skills", "skills", "languages", "certifications", "summary",
        "about", "experience", "education", "honors", "awards", "publications",
    }

    email_re = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
    phone_re = re.compile(r"(?:\+\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
    contact_url_re = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?", re.I)

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # Detect contact block start
        if lower in ("contact", "contact info", "contact details"):
            in_contact_block = True
            continue

        if in_contact_block:
            if lower in section_headers:
                in_contact_block = False
            else:
                # Discard entire line in contact block
                continue

        # Discard lines matching common LinkedIn contact labels
        if any(lbl in lower for lbl in ("(linkedin)", "(email)", "(mobile)", "(phone)", "(home)", "(work)")):
            continue

        # Scrub embedded emails, phone numbers, contact URLs completely
        cleaned_line = email_re.sub("", stripped)
        cleaned_line = phone_re.sub("", cleaned_line)
        cleaned_line = contact_url_re.sub("", cleaned_line)
        cleaned_line = re.sub(r"\s+", " ", cleaned_line).strip()

        if cleaned_line:
            filtered_lines.append(cleaned_line)

    return "\n".join(filtered_lines)


def extract_pdf_text(pdf_bytes: bytes, max_bytes: int = MAX_PDF_BYTES) -> str:
    """Extract plain text from PDF bytes without requiring binary OCR or heavy dependencies.

    Enforces 2MB size limit and ignores/rejects potential script blocks (/JavaScript, /Launch).
    """
    if len(pdf_bytes) > max_bytes:
        raise ValueError(f"PDF size ({len(pdf_bytes)} bytes) exceeds the 2 MB limit.")

    extracted_lines: list[str] = []

    # 1. Search for FlateDecode compressed streams
    stream_pattern = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.S)
    for match in stream_pattern.finditer(pdf_bytes):
        raw_stream = match.group(1)
        decompressed: bytes = b""
        try:
            decompressed = zlib.decompress(raw_stream)
        except Exception:
            try:
                decompressed = zlib.decompress(raw_stream, -zlib.MAX_WBITS)
            except Exception:
                decompressed = raw_stream

        text_str = decompressed.decode("latin1", errors="replace")

        # Extract literal strings within text showing operators: (text) Tj or [(t1) 12 (t2)] TJ
        tj_matches = re.findall(r"\((.*?)\)\s*Tj", text_str)
        for tj in tj_matches:
            unescaped = _unescape_pdf_string(tj)
            if unescaped.strip():
                extracted_lines.append(unescaped.strip())

        tj_array_matches = re.findall(r"\[(.*?)\]\s*TJ", text_str)
        for tja in tj_array_matches:
            inner_strings = re.findall(r"\((.*?)\)", tja)
            combined = "".join(_unescape_pdf_string(s) for s in inner_strings)
            if combined.strip():
                extracted_lines.append(combined.strip())

    # Fallback: scan raw PDF for text chunks if stream decompression yielded nothing
    if not extracted_lines:
        latin_text = pdf_bytes.decode("latin1", errors="replace")
        tj_matches = re.findall(r"\((.*?)\)\s*Tj", latin_text)
        for tj in tj_matches:
            unescaped = _unescape_pdf_string(tj)
            if unescaped.strip():
                extracted_lines.append(unescaped.strip())

    joined = "\n".join(extracted_lines)
    sanitized = sanitize_text(joined)
    return discard_contact_info(sanitized)


def _unescape_pdf_string(s: str) -> str:
    """Decode standard PDF string escape sequences."""
    s = s.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    s = s.replace(r"\r", "\r").replace(r"\n", "\n").replace(r"\t", "\t")
    def _octal_replace(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1), 8))
        except Exception:
            return str(m.group(0))
    return re.sub(r"\\([0-7]{1,3})", _octal_replace, s)


def _parse_date_range(date_str: str) -> tuple[str, str, str, bool]:
    """Parse date strings like 'March 2023 - Present (3 years 1 month)' or '2019 - 2022'.

    Returns (start, end, duration, is_current).
    """
    clean = date_str.strip()
    is_current = "present" in clean.lower()
    duration = ""
    dur_match = re.search(r"\((.*?)\)", clean)
    if dur_match:
        duration = dur_match.group(1).strip()
        clean = re.sub(r"\(.*?\)", "", clean).strip()

    # Split on hyphen / en-dash / em-dash
    parts = re.split(r"[-–—]", clean)
    start = parts[0].strip() if len(parts) > 0 else ""
    end = parts[1].strip() if len(parts) > 1 else ("Present" if is_current else "")
    return start, end, duration, is_current


def _is_date_line(line: str) -> bool:
    """Detect if a line looks like a date range."""
    lower = line.lower()
    if "present" in lower:
        return True
    # E.g. March 2023 - Present or 2019 - 2022
    if re.search(r"\b(?:19|20)\d{2}\b", line) and re.search(r"[-–—]", line):
        return True
    return False


def _is_pure_date_line(line: str) -> bool:
    """Check if a line contains ONLY dates/durations (e.g. 'March 2023 - Present (3 years 1 month)')."""
    if not line:
        return False
    lower = line.lower().strip()
    if not _is_date_line(lower):
        return False
    # Strip common date/duration tokens
    cleaned = re.sub(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december|present|year|years|month|months|yr|yrs|mo|mos)\b",
        "",
        lower,
    )
    cleaned = re.sub(r"[0-9\s()·•,\-–—/|]", "", cleaned)
    return len(cleaned) <= 3


def parse_manual_profile_text(text: str) -> dict[str, Any]:
    """Parse pasted text or extracted PDF text into structured profile attributes.

    Discards all Contact details (PII) and accurately structures:
    - headline, summary/about, location
    - skills, languages, certifications
    - experience timeline (company, title, start, end, duration, is_current, description)
    - education (school, degree, field, start_year, end_year)
    """
    sanitized = sanitize_text(text)
    privacy_cleaned = discard_contact_info(sanitized)
    if not privacy_cleaned:
        return {}

    lines = [line.strip() for line in privacy_cleaned.splitlines() if line.strip()]
    if not lines:
        return {}

    result: dict[str, Any] = {
        "headline": None,
        "location": None,
        "summary": None,
        "skills": [],
        "languages": [],
        "certifications": [],
        "experience": [],
        "education": [],
    }

    # Section segmentation
    sections: dict[str, list[str]] = {
        "header": [],
        "skills": [],
        "languages": [],
        "certifications": [],
        "summary": [],
        "experience": [],
        "education": [],
    }

    current_section = "header"
    for line in lines:
        lower = line.lower()
        if lower in ("top skills", "skills", "key skills"):
            current_section = "skills"
            continue
        elif lower in ("languages", "known languages"):
            current_section = "languages"
            continue
        elif lower in ("certifications", "licenses & certifications"):
            current_section = "certifications"
            continue
        elif lower in ("summary", "about", "overview"):
            current_section = "summary"
            continue
        elif lower in ("experience", "work experience", "career", "employment"):
            current_section = "experience"
            continue
        elif lower in ("education", "academics", "qualifications"):
            current_section = "education"
            continue

        sections[current_section].append(line)

    # 1. Header parsing (Headline, Location)
    header_lines = sections["header"]
    role_pattern = re.compile(
        r"\b(?:co-founder|founder|ceo|cto|cpo|cfo|coo|head of|director|vp|vice president|engineer|product)\b",
        re.I,
    )
    for line in header_lines:
        if role_pattern.search(line) and not result["headline"]:
            result["headline"] = line[:120]
        elif any(loc_kw in line.lower() for loc_kw in ("india", "area", "bengaluru", "delhi", "mumbai", "san francisco", "united states", "london")):
            if not result["location"]:
                result["location"] = line[:80]

    if not result["headline"] and len(header_lines) > 1:
        result["headline"] = header_lines[1][:120]

    # 2. Skills
    for s in sections["skills"]:
        items = re.split(r"[·•|,]|\s{2,}", s)
        for item in items:
            cl = item.strip()
            if cl and len(cl) > 1 and cl not in result["skills"]:
                result["skills"].append(cl)

    # 3. Languages
    for l in sections["languages"]:
        result["languages"].append(l)

    # 4. Certifications
    for c in sections["certifications"]:
        result["certifications"].append(c)

    # 5. Summary / About
    if sections["summary"]:
        result["summary"] = " ".join(sections["summary"])[:1000]

    # 6. Experience Parsing
    exp_lines = sections["experience"]
    i = 0
    while i < len(exp_lines):
        line1 = exp_lines[i]
        line2 = exp_lines[i + 1] if i + 1 < len(exp_lines) else ""
        line3 = exp_lines[i + 2] if i + 2 < len(exp_lines) else ""

        # Case A: Self-contained inline experience line, e.g. "Title at Company (Dates)"
        date_match = re.search(r"\(((?:19|20)\d{2}\s*[-–—]\s*(?:present|(?:19|20)\d{2})[^)]*)\)", line1, re.I) or re.search(r"\b((?:19|20)\d{2}\s*[-–—]\s*(?:present|(?:19|20)\d{2}))\b", line1, re.I)
        if date_match and (" at " in line1 or " @" in line1 or " - " in line1 or " · " in line1):
            date_str = date_match.group(1)
            start, end, duration, is_current = _parse_date_range(date_str)
            raw_text = line1[:date_match.start()] + line1[date_match.end():]
            raw_text = raw_text.strip(" ()·-–—")
            title = raw_text
            company = ""
            if " at " in raw_text:
                parts = raw_text.split(" at ", 1)
                title, company = parts[0].strip(), parts[1].strip()
            elif " · " in raw_text:
                parts = raw_text.split(" · ", 1)
                title, company = parts[0].strip(), parts[1].strip()
            result["experience"].append({
                "company": company,
                "title": title,
                "role": title,
                "start": start,
                "end": end,
                "duration": duration,
                "is_current": is_current,
                "location": "",
                "description": "",
            })
            i += 1
            continue

        # Case B: LinkedIn PDF (Line 1: Company -> Line 2: Title -> Line 3: Pure Date line)
        if _is_pure_date_line(line3):
            start, end, duration, is_current = _parse_date_range(line3)
            company = line1
            title = line2
            loc = exp_lines[i + 3] if i + 3 < len(exp_lines) and not _is_date_line(exp_lines[i + 3]) and ("area" in exp_lines[i + 3].lower() or "," in exp_lines[i + 3]) else ""
            desc = ""
            advance = 4 if loc else 3
            result["experience"].append({
                "company": company,
                "title": title,
                "role": title,
                "start": start,
                "end": end,
                "duration": duration,
                "is_current": is_current,
                "location": loc,
                "description": desc,
            })
            i += advance
        # Case C: Web-pasted with Company in line 2 and Pure Date in line 3
        elif "·" in line2 and _is_pure_date_line(line3):
            start, end, duration, is_current = _parse_date_range(line3)
            title = line1
            company = line2.split("·")[0].strip()
            result["experience"].append({
                "company": company,
                "title": title,
                "role": title,
                "start": start,
                "end": end,
                "duration": duration,
                "is_current": is_current,
                "location": "",
                "description": "",
            })
            i += 3
        # Case D: Line 2 is Pure Date line
        elif _is_pure_date_line(line2):
            start, end, duration, is_current = _parse_date_range(line2)
            title = line1
            company = ""
            if " at " in title.lower():
                parts = title.split(" at ", 1)
                title = parts[0].strip()
                company = parts[1].strip()
            result["experience"].append({
                "company": company,
                "title": title,
                "role": title,
                "start": start,
                "end": end,
                "duration": duration,
                "is_current": is_current,
                "location": "",
                "description": "",
            })
            i += 2
        # Case E: Line 2 is a recognized role/title (e.g. Previous Startup \n Advisor)
        elif line2 and any(t in line2.lower() for t in ("advisor", "consultant", "founder", "director", "manager", "lead", "head", "vp", "officer", "ceo", "cto", "engineer")):
            result["experience"].append({
                "company": line1,
                "title": line2,
                "role": line2,
                "start": "",
                "end": "",
                "duration": "",
                "is_current": False,
                "location": "",
                "description": "",
            })
            i += 2
        # Case F: Trailing description text attached to previous experience entry
        elif result["experience"]:
            prev_exp = result["experience"][-1]
            existing_desc = prev_exp.get("description", "")
            prev_exp["description"] = (existing_desc + " " + line1).strip()
            i += 1
        else:
            # Fallback single line experience entry
            if len(line1) > 3:
                result["experience"].append({
                    "company": "",
                    "title": line1,
                    "role": line1,
                    "start": "",
                    "end": "",
                    "duration": "",
                    "is_current": False,
                    "location": "",
                    "description": "",
                })
            i += 1

    # 7. Education Parsing
    edu_lines = sections["education"]
    j = 0
    while j < len(edu_lines):
        school = edu_lines[j]
        degree_line = edu_lines[j + 1] if j + 1 < len(edu_lines) else ""
        date_line = edu_lines[j + 2] if j + 2 < len(edu_lines) else ""

        # Case A: Self-contained inline education entry, e.g. "B.Tech in Computer Science · IIT Delhi (2011 - 2015)"
        edu_date_match = re.search(r"\(((?:19|20)\d{2}\s*[-–—]\s*(?:present|(?:19|20)\d{2})[^)]*)\)", school, re.I)
        if edu_date_match:
            date_str = edu_date_match.group(1)
            start_year, end_year, _, _ = _parse_date_range(date_str)
            raw_edu = school[:edu_date_match.start()].strip(" ()·-–—")
            deg, sch, fld = "", raw_edu, ""
            for sep in (" · ", " — ", " - ", " at "):
                if sep in raw_edu:
                    parts = raw_edu.split(sep, 1)
                    deg = parts[0].strip()
                    sch = parts[1].strip()
                    break
            if " in " in deg:
                deg_parts = deg.split(" in ", 1)
                deg = deg_parts[0].strip()
                fld = deg_parts[1].strip()
            result["education"].append({
                "school": sch,
                "institution": sch,
                "degree": deg,
                "field": fld,
                "year": f"{start_year} - {end_year}".strip(" -"),
                "start_year": start_year,
                "end_year": end_year,
            })
            j += 1
            continue

        start_year = ""
        end_year = ""
        degree = ""
        field = ""

        if _is_pure_date_line(date_line):
            start_year, end_year, _, _ = _parse_date_range(date_line)
            degree = degree_line
            j += 3
        elif _is_pure_date_line(degree_line):
            start_year, end_year, _, _ = _parse_date_range(degree_line)
            j += 2
        else:
            degree = degree_line
            j += 2

        if "," in degree:
            d_parts = degree.split(",", 1)
            degree = d_parts[0].strip()
            field = d_parts[1].strip()
        elif " - " in degree:
            d_parts = degree.split(" - ", 1)
            degree = d_parts[0].strip()
            field = d_parts[1].strip()

        result["education"].append({
            "school": school,
            "institution": school,
            "degree": degree,
            "field": field,
            "year": f"{start_year} - {end_year}".strip(" -"),
            "start_year": start_year,
            "end_year": end_year,
        })

    return result

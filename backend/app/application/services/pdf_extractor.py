"""Pure-Python PDF text extraction and script sanitization for manual evidence provision.

Respects strict 2MB memory budget, strips executable scripts / HTML tags, and parses profile text.
Pure Python standard library only (re, zlib, html, base64).
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

    # Fallback: if stream extraction didn't yield text, scan raw PDF for text chunks
    if not extracted_lines:
        latin_text = pdf_bytes.decode("latin1", errors="replace")
        tj_matches = re.findall(r"\((.*?)\)\s*Tj", latin_text)
        for tj in tj_matches:
            unescaped = _unescape_pdf_string(tj)
            if unescaped.strip():
                extracted_lines.append(unescaped.strip())

    joined = "\n".join(extracted_lines)
    return sanitize_text(joined)


def _unescape_pdf_string(s: str) -> str:
    """Decode standard PDF string escape sequences."""
    s = s.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    s = s.replace(r"\r", "\r").replace(r"\n", "\n").replace(r"\t", "\t")
    def _octal_replace(m: re.Match) -> str:
        try:
            return chr(int(m.group(1), 8))
        except Exception:
            return m.group(0)
    return re.sub(r"\\([0-7]{1,3})", _octal_replace, s)


def parse_manual_profile_text(text: str) -> dict[str, Any]:
    """Parse pasted text or extracted PDF text into structured profile attributes."""
    cleaned = sanitize_text(text)
    if not cleaned:
        return {}

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return {}

    result: dict[str, Any] = {
        "headline": None,
        "summary": None,
        "experience": [],
        "education": [],
        "description": cleaned[:800],
    }

    role_pattern = re.compile(
        r"\b(?:co-founder|founder|ceo|cto|cpo|cfo|coo|head of|director|vp|vice president|engineer|product)\b",
        re.I,
    )
    for line in lines[:5]:
        if role_pattern.search(line):
            result["headline"] = line[:120]
            break
    if not result["headline"] and len(lines) > 1:
        result["headline"] = lines[1][:120]

    current_sec = "none"
    exp_lines: list[str] = []
    edu_lines: list[str] = []
    summary_lines: list[str] = []

    for line in lines:
        line_lower = line.lower()
        if line_lower in ("experience", "work experience", "career", "employment"):
            current_sec = "exp"
            continue
        elif line_lower in ("education", "academics", "qualifications"):
            current_sec = "edu"
            continue
        elif line_lower in ("about", "summary", "overview"):
            current_sec = "summary"
            continue

        if current_sec == "exp":
            exp_lines.append(line)
        elif current_sec == "edu":
            edu_lines.append(line)
        elif current_sec == "summary":
            summary_lines.append(line)

    if summary_lines:
        result["summary"] = " ".join(summary_lines[:5])[:600]

    if exp_lines:
        for l in exp_lines[:6]:
            if len(l) > 3:
                result["experience"].append({"role": l, "company": ""})

    if edu_lines:
        for l in edu_lines[:4]:
            if len(l) > 3:
                result["education"].append({"institution": l, "degree": ""})

    return result

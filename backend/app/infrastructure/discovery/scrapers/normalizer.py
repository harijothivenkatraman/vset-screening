"""Normalizer utilities for URLs, text, and scraped entities."""
from __future__ import annotations

import re
import urllib.parse
from typing import Any


TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "source", "_hsenc", "_hsmi",
})


def clean_url(url: str) -> str:
    """Normalize a URL by lowercasing scheme/host, stripping tracking params, and removing fragment."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        clean_query = urllib.parse.urlencode(filtered_query)
        cleaned = urllib.parse.urlunsplit((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            clean_query,
            "",  # strip fragment
        ))
        return cleaned
    except Exception:
        return url.strip()


def canonicalize_url(url: str) -> str:
    """Canonicalize a URL: lowercase scheme and host, strip www., query params, fragment, and trailing slashes."""
    if not url:
        return ""
    try:
        u = url.strip()
        if not u.startswith(("http://", "https://")):
            u = f"https://{u}"
        parsed = urllib.parse.urlsplit(u)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        clean_query = urllib.parse.urlencode(filtered_query)
        return urllib.parse.urlunsplit((
            scheme,
            netloc,
            path,
            clean_query,
            "",
        ))
    except Exception:
        return url.strip()


BOILERPLATE_PATTERNS = [
    re.compile(r"\b(?:online now|expert is available|talk to us|chat with us|leave a message|we're online|we are online|how can we help|typically replies|reply time|agents? online)\b", re.I),
    re.compile(r"\b(?:accept all cookies|cookie policy|we use cookies|privacy policy|terms of service|manage preferences|all rights reserved)\b", re.I),
    re.compile(r"\b(?:oops! something went wrong|submitting the form|submission has been received)\b", re.I),
]


def is_boilerplate_line(line: str) -> bool:
    """Return True if line matches chat-widget, cookie banner, or form boilerplate."""
    if not line:
        return True
    l_strip = line.strip()
    return any(p.search(l_strip) is not None for p in BOILERPLATE_PATTERNS)


def clean_text(text: Any) -> str:
    """Clean scraped text: normalize whitespace, collapse blank lines, replace smart quotes/dashes."""
    if not text:
        return ""
    if isinstance(text, (list, tuple, set)):
        text = ", ".join(str(item).strip() for item in text if item)
    elif not isinstance(text, str):
        text = str(text)

    # Normalize quotes and dashes
    t = text.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2014", " - ").replace("\u2013", " - ")

    # Collapse excessive whitespace
    lines = [line.strip() for line in t.splitlines()]
    # Remove empty line runs
    cleaned_lines: list[str] = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned_lines.append("")
                prev_empty = True
        else:
            cleaned_lines.append(re.sub(r"[ \t]+", " ", line))
            prev_empty = False

    return "\n".join(cleaned_lines).strip()


def extract_year(text: str | None) -> str | None:
    """Extract a 4-digit year from a date string or text."""
    if not text:
        return None
    match = re.search(r"\b(19\d\d|20\d\d)\b", str(text))
    return match.group(1) if match else None


def deduplicate_list(items: list[str]) -> list[str]:
    """Deduplicate a list of strings while preserving initial order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item_clean = item.strip()
        if item_clean and item_clean.lower() not in seen:
            seen.add(item_clean.lower())
            result.append(item_clean)
    return result

"""SSRF protection utilities.

Ensures that outbound HTTP requests from scrapers and fetchers
only target public IPv4/IPv6 addresses and standard HTTP/HTTPS schemes.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import Final

ALLOWED_SCHEMES: Final[set[str]] = {"http", "https"}

FORBIDDEN_FETCH_DOMAINS: Final[set[str]] = {
    "crunchbase.com",
    "pitchbook.com",
    "zoominfo.com",
    "g2.com",
    "tracxn.com",
    "trustpilot.com",
}


def is_forbidden_fetch_domain(target: str) -> bool:
    """Check if a domain or URL belongs to the fetch denylist."""
    if "://" in target or "/" in target:
        try:
            parsed = urllib.parse.urlsplit(target if "://" in target else f"http://{target}")
            host = parsed.netloc or parsed.path.split("/")[0]
        except Exception:
            host = target
    else:
        host = target
    clean = host.split(":")[0].strip("[]").lower()
    for domain in FORBIDDEN_FETCH_DOMAINS:
        if clean == domain or clean.endswith("." + domain):
            return True
    return False


def is_ip_private_or_reserved(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to private, loopback, link-local, or reserved networks."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_safe_url(url: str, *, resolve_dns: bool = True) -> str:
    """Validate that a URL is safe to fetch and does not target internal infrastructure.

    Args:
        url: The candidate URL to validate.
        resolve_dns: Whether to perform DNS resolution to verify the target IP.

    Returns:
        The validated URL.

    Raises:
        ValueError: If the URL scheme is unsupported or resolves to private/loopback/link-local address.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    parsed = urllib.parse.urlsplit(url.strip())
    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed URL scheme '{scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid URL: missing hostname in '{url}'")

    hostname_clean = hostname.strip("[]").lower()

    # 1. Directly check literal IP
    try:
        ip = ipaddress.ip_address(hostname_clean)
        if is_ip_private_or_reserved(ip):
            raise ValueError(f"Blocked private/reserved IP target '{ip}'")
        return url
    except ValueError as e:
        if "Blocked" in str(e):
            raise
        # Not a literal IP, proceed to domain checks

    # 2. Block well-known local hostnames
    if hostname_clean in {"localhost", "localhost.localdomain", "broadcasthost"}:
        raise ValueError(f"Blocked loopback hostname '{hostname_clean}'")

    if hostname_clean.endswith(".local") or hostname_clean.endswith(".internal"):
        raise ValueError(f"Blocked private TLD in '{hostname_clean}'")

    # 3. Block login-gated/ToS-restricted data broker domains from direct fetching
    if is_forbidden_fetch_domain(hostname_clean):
        raise ValueError(f"Blocked forbidden fetch domain '{hostname_clean}'")

    # 3. DNS resolution check if enabled
    if resolve_dns:
        try:
            addr_info = socket.getaddrinfo(hostname_clean, None)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                resolved_ip = ipaddress.ip_address(ip_str)
                if is_ip_private_or_reserved(resolved_ip):
                    raise ValueError(
                        f"Blocked hostname '{hostname_clean}' resolving to private/reserved IP '{resolved_ip}'"
                    )
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for '{hostname_clean}': {e}") from e

    return url


def is_safe_url(url: str, *, resolve_dns: bool = True) -> bool:
    """Convenience boolean check for validate_safe_url."""
    try:
        validate_safe_url(url, resolve_dns=resolve_dns)
        return True
    except ValueError:
        return False

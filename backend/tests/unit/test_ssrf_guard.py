"""Unit tests for SSRF guard."""
from __future__ import annotations

import pytest

from app.infrastructure.discovery.http.ssrf_guard import is_safe_url, validate_safe_url


class TestSsrfGuard:
    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://127.0.0.1/admin",
            "http://127.0.0.2:8080",
            "http://10.0.0.5/api",
            "http://192.168.1.1/",
            "http://172.16.0.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost:8000",
            "http://localhost.localdomain",
            "http://test.local",
            "http://internal.service.internal",
            "ftp://example.com/file",
            "file:///etc/passwd",
            "gopher://example.com",
            "",
            "   ",
        ],
    )
    def test_blocks_internal_and_disallowed_urls(self, bad_url: str) -> None:
        assert not is_safe_url(bad_url, resolve_dns=False)
        with pytest.raises(ValueError):
            validate_safe_url(bad_url, resolve_dns=False)

    @pytest.mark.parametrize(
        "good_url",
        [
            "https://example.com",
            "http://www.google.com/search?q=test",
            "https://linkedin.com/company/acme",
            "https://93.184.216.34/",  # example.com public IP
        ],
    )
    def test_allows_public_urls(self, good_url: str) -> None:
        assert is_safe_url(good_url, resolve_dns=False)
        validated = validate_safe_url(good_url, resolve_dns=False)
        assert validated == good_url

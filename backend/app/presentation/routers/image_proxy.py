"""Secure image proxy endpoint for LinkedIn profile and company assets."""
from __future__ import annotations

import logging
import urllib.parse
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import httpx

from app.config import get_settings
from app.infrastructure.discovery.http.ssrf_guard import validate_safe_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["image-proxy"])
settings = get_settings()

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2MB max


@router.get("/image-proxy")
async def proxy_image(url: str = Query(..., description="Target image URL to proxy")) -> StreamingResponse:
    """Safely stream external profile and company images through backend cache.

    Restricted to configured allowed hosts (e.g. media.licdn.com, static.licdn.com).
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image URL query parameter is required.",
        )

    # 1. Parse and validate host against allowlist
    parsed = urllib.parse.urlsplit(url.strip())
    hostname = (parsed.hostname or "").lower()
    allowed_hosts = [h.lower() for h in settings.IMAGE_PROXY_ALLOWED_HOSTS]

    if not any(hostname == h or hostname.endswith(f".{h}") for h in allowed_hosts):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Image host '{hostname}' is not in the allowed image proxy hosts.",
        )

    # 2. SSRF check
    try:
        validate_safe_url(url, resolve_dns=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF validation failed: {exc}",
        ) from exc

    # 3. Stream image from upstream
    client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
    try:
        req = client.build_request("GET", url, headers={"User-Agent": "vSET-Proxy/1.0"})
        resp = await client.send(req, stream=True)

        if resp.status_code != 200:
            await resp.aclose()
            await client.aclose()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream image fetch returned HTTP {resp.status_code}",
            )

        content_type = resp.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            await resp.aclose()
            await client.aclose()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target content-type '{content_type}' is not a valid image.",
            )

        async def _stream_content() -> AsyncGenerator[bytes, None]:
            total_bytes = 0
            try:
                async for chunk in resp.aiter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > MAX_IMAGE_BYTES:
                        break
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(
            _stream_content(),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400, immutable",
            },
        )
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch upstream image: {exc}",
        ) from exc

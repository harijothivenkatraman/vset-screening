import hmac
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_admin_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str:
    settings = get_settings()
    expected_key = settings.IMPORT_API_KEY

    # Use constant-time comparison to prevent timing attacks
    if not api_key or not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key in 'X-API-Key' header",
        )

    # In production, refuse admin calls over plain HTTP unless from localhost
    if settings.ENVIRONMENT.lower() == "production":
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "")
        host_header = request.headers.get("host", "").split(":")[0].lower()

        is_localhost = client_ip in ("127.0.0.1", "::1", "localhost") or host_header in ("localhost", "127.0.0.1")

        if proto != "https" and not is_localhost:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin operations over plain HTTP are refused in production unless originating from localhost/SSH tunnel. Use HTTPS or an SSH port forward.",
            )

    return api_key


# Backwards compatibility alias
verify_api_key = verify_admin_key



async def verify_read_or_admin_key(api_key: str | None = Security(api_key_header)) -> str | None:
    settings = get_settings()
    admin_key = settings.IMPORT_API_KEY
    read_key = settings.READ_API_KEY

    # Public read mode
    if not read_key:
        return api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key in 'X-API-Key' header",
        )

    if hmac.compare_digest(api_key, admin_key):
        return api_key

    if hmac.compare_digest(api_key, read_key):
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key in 'X-API-Key' header",
    )

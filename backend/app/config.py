from functools import lru_cache
import json
from typing import Any
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """
    Normalizes database connection strings for asyncpg / aiosqlite:
    - postgres:// -> postgresql+asyncpg://
    - postgresql:// -> postgresql+asyncpg://
    - converts ?sslmode=... or &sslmode=... to ?ssl=... or &ssl=... (asyncpg requirement)
    """
    if not isinstance(url, str):
        return url

    res = url.strip()
    if res.startswith("postgres://"):
        res = "postgresql+asyncpg://" + res[len("postgres://") :]
    elif res.startswith("postgresql://") and not res.startswith("postgresql+asyncpg://"):
        res = "postgresql+asyncpg://" + res[len("postgresql://") :]

    # asyncpg does not accept 'sslmode', requires 'ssl'
    if "sslmode=" in res:
        res = res.replace("sslmode=", "ssl=")

    return res


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./vset.db"
    IMPORT_API_KEY: str = "dev-insecure-test-key-32-chars-long-00000"
    READ_API_KEY: str | None = None  # None = public read mode (no key required for GET)
    CORS_ORIGINS: list[str] = ["*"]
    ENVIRONMENT: str = "development"

    # Scraper & Rate Limit Settings
    SCRAPER_MIN_INTERVAL: float = 3.0
    RATE_LIMIT_FETCH_PER_MINUTE_IP: int = 10
    RATE_LIMIT_FETCH_PER_MINUTE_GLOBAL: int = 30

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Any) -> str:
        if isinstance(v, str):
            return normalize_database_url(v)
        return str(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_string_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            val = v.strip()
            if not val:
                return []
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed]
                except Exception:
                    pass
            return [o.strip() for o in val.split(",") if o.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(o).strip() for o in v]
        return []

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            # 1. Fail closed on missing, short, or example API keys
            key = (self.IMPORT_API_KEY or "").strip()
            if not key:
                raise ValueError("IMPORT_API_KEY must be provided in production.")
            if len(key) < 32:
                raise ValueError(
                    f"IMPORT_API_KEY must be at least 32 characters in production (got {len(key)})."
                )

            lower_key = key.lower()
            insecure_patterns = [
                "vset-secret",
                "changeme",
                "replace-me",
                "example-key",
                "admin-key",
                "password",
                "12345678",
                "dev-insecure",
                "dev-read-only",
            ]
            if any(p in lower_key for p in insecure_patterns):
                raise ValueError(
                    "IMPORT_API_KEY cannot be set to a known default or example value in production."
                )

            read_key = (self.READ_API_KEY or "").strip()
            if read_key:
                if len(read_key) < 32:
                    raise ValueError(
                        f"READ_API_KEY must be at least 32 characters in production (got {len(read_key)})."
                    )
                if any(p in read_key.lower() for p in insecure_patterns):
                    raise ValueError(
                        "READ_API_KEY cannot be set to a known default or example value in production."
                    )

            # 2. CORS: reject '*' wildcard in production
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CORS_ORIGINS cannot contain '*' wildcard in production. Specify exact origins or leave empty for same-origin."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

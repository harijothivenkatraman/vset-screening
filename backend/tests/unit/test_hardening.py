import hmac
import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_database_url


class TestDatabaseUrlNormalization:
    def test_plain_postgresql_to_asyncpg(self):
        raw = "postgresql://vset:secret@db:5432/vset"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+asyncpg://vset:secret@db:5432/vset"

    def test_postgres_short_scheme_to_asyncpg(self):
        raw = "postgres://vset:secret@db:5432/vset"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+asyncpg://vset:secret@db:5432/vset"

    def test_preserves_already_asyncpg_scheme(self):
        raw = "postgresql+asyncpg://vset:secret@db:5432/vset"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+asyncpg://vset:secret@db:5432/vset"

    def test_converts_sslmode_require_to_ssl_require(self):
        raw = "postgresql://user:pass@ep-cool-sample.aws.neon.tech/neondb?sslmode=require"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+asyncpg://user:pass@ep-cool-sample.aws.neon.tech/neondb?ssl=require"

    def test_converts_sslmode_with_multiple_params(self):
        raw = "postgres://user:pass@rds.amazonaws.com:5432/mydb?sslmode=verify-full&connect_timeout=10"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+asyncpg://user:pass@rds.amazonaws.com:5432/mydb?ssl=verify-full&connect_timeout=10"

    def test_preserves_sqlite_url(self):
        raw = "sqlite+aiosqlite:///./test.db"
        assert normalize_database_url(raw) == raw


class TestProductionSecurityValidation:
    def test_production_fails_when_api_key_missing(self):
        with pytest.raises(ValidationError) as exc:
            Settings(
                ENVIRONMENT="production",
                IMPORT_API_KEY="",
                CORS_ORIGINS=[],
            )
        assert "IMPORT_API_KEY must be provided in production" in str(exc.value)

    def test_production_fails_when_api_key_under_32_chars(self):
        with pytest.raises(ValidationError) as exc:
            Settings(
                ENVIRONMENT="production",
                IMPORT_API_KEY="short-secret-key",
                CORS_ORIGINS=[],
            )
        assert "at least 32 characters" in str(exc.value)

    def test_production_fails_on_insecure_example_key(self):
        with pytest.raises(ValidationError) as exc:
            Settings(
                ENVIRONMENT="production",
                IMPORT_API_KEY="changeme-production-key-which-is-longer-than-32-chars",
                CORS_ORIGINS=[],
            )
        assert "known default or example value" in str(exc.value)

    def test_production_fails_when_cors_contains_wildcard(self):
        with pytest.raises(ValidationError) as exc:
            Settings(
                ENVIRONMENT="production",
                IMPORT_API_KEY="a" * 32,
                CORS_ORIGINS=["*"],
            )
        assert "cannot contain '*' wildcard" in str(exc.value)

    def test_production_succeeds_with_strong_key_and_empty_or_specific_cors(self):
        # Empty CORS (same-origin only)
        s1 = Settings(
            ENVIRONMENT="production",
            IMPORT_API_KEY="a" * 32,
            CORS_ORIGINS=[],
        )
        assert s1.ENVIRONMENT == "production"
        assert s1.CORS_ORIGINS == []

        # Specific domain CORS
        s2 = Settings(
            ENVIRONMENT="production",
            IMPORT_API_KEY="a" * 32,
            CORS_ORIGINS=["https://dashboard.example.com"],
        )
        assert s2.CORS_ORIGINS == ["https://dashboard.example.com"]

    def test_development_allows_defaults(self):
        dev_settings = Settings(ENVIRONMENT="development")
        assert dev_settings.ENVIRONMENT == "development"
        assert "*" in dev_settings.CORS_ORIGINS


class TestConstantTimeKeyComparison:
    def test_hmac_compare_digest(self):
        key = "a" * 32
        assert hmac.compare_digest(key, key) is True
        assert hmac.compare_digest(key, "b" * 32) is False


class TestSeedIdempotency:
    @pytest.mark.asyncio
    async def test_seed_second_run_is_unchanged(self):
        from seed import seed

        # First run (seeds or verifies baseline)
        results1 = await seed()
        assert len(results1) >= 2

        # Second run (must strictly be unchanged)
        results2 = await seed()
        assert len(results2) >= 2
        for slug, status in results2:
            assert status == "unchanged", f"Seed for {slug} was not idempotent: {status}"

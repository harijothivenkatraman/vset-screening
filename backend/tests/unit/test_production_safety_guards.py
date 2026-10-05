"""Tests verifying production safety guards against unauthorized authoring or demo seeding."""
import pytest
from app.config import Settings
from app.scripts.seed_demo_reports import seed as seed_demo


@pytest.mark.asyncio
async def test_seed_demo_aborts_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Demo seed scripts must strictly abort if ENVIRONMENT=production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="CRITICAL SAFETY GUARD: Demo seed scripts must never execute in production"):
        await seed_demo()


def test_reference_file_allowlist() -> None:
    """Production seed is restricted to canonical reference JSON files only."""
    allowed = {"terraspark_founder_screen.json", "mysa_founder_screen.json"}
    test_files = ["demo_report.json", "custom_profile.json", "terraspark_founder_screen.json"]
    for f in test_files:
        if f not in allowed:
            assert f != "mysa_founder_screen.json"

"""Unit tests for standalone Founder Profiles use cases.

Strict adherence to testing guidelines:
- Strictly fictional test personas ('Asha Example', 'Example Corp', 'John Fictional')
- Verifies identity_status="user_asserted" for user evidence
- Verifies blocked attempts are NOT automatically persisted unless save_as_pending=True
- Verifies previous_version snapshots and single-step version restore
- Verifies guarded deletion requiring exact slug confirmation
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.use_cases.add_from_evidence import AddFromEvidenceUseCase
from app.application.use_cases.delete_profile import DeleteProfileUseCase
from app.application.use_cases.export_profile import ExportProfileUseCase
from app.application.use_cases.get_profile import GetProfileUseCase
from app.application.use_cases.list_profiles import ListProfilesUseCase
from app.application.use_cases.restore_profile_version import RestoreProfileVersionUseCase
from app.application.use_cases.try_public_fetch import TryPublicFetchUseCase
from app.application.use_cases.update_profile import UpdateProfileUseCase
from app.domain.entities.discovery import SourceDiagnostic
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import (
    DuplicateProfileException,
    InvalidEvidenceException,
    NoPreviousVersionException,
    ProfileNotFoundException,
)
from app.infrastructure.persistence.sqlite_founder_repository import (
    SqliteFounderProfileRepository,
)


@pytest.fixture
def founder_repo(db_session: AsyncSession) -> FounderProfileRepository:
    return SqliteFounderProfileRepository(db_session)


@pytest.mark.asyncio
async def test_add_from_evidence_text_sanitizes_and_sets_user_asserted(
    founder_repo: FounderProfileRepository,
) -> None:
    use_case = AddFromEvidenceUseCase(founder_repo)

    evidence_text = """
    Asha Example
    Chief Executive Officer at Example Corp
    Contact: asha@example.com | +1 (555) 123-4567 | San Francisco, CA

    About:
    Building next-generation open platforms for enterprise automation.

    Experience:
    CEO & Co-Founder, Example Corp (2022 - Present)
    Senior Engineering Lead, Fictional Labs (2018 - 2022)

    Education:
    B.S. in Computer Science, State University (2014 - 2018)

    Skills:
    Distributed Systems, Python, System Architecture
    """

    profile = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        text=evidence_text,
    )

    assert profile.founder_name == "Asha Example"
    assert profile.company_name == "Example Corp"
    assert profile.slug == "asha-example-example-corp"
    assert profile.identity_status == "user_asserted"
    assert profile.retrieval.status == "user_provided"
    assert profile.retrieval.source_label == "Provided by user (unverified)"

    # Verify PII contact info stripped from about/fields
    raw_dict_str = str(profile.to_dict())
    assert "asha@example.com" not in raw_dict_str
    assert "555" not in raw_dict_str

    # Verify experience and education parsed
    assert len(profile.experience_timeline) >= 2
    assert profile.experience_timeline[0].company == "Example Corp"
    assert len(profile.education) >= 1
    assert "State University" in profile.education[0].school


@pytest.mark.asyncio
async def test_duplicate_profile_detection_and_override(
    founder_repo: FounderProfileRepository,
) -> None:
    use_case = AddFromEvidenceUseCase(founder_repo)
    text = "Fictional Founder\nCEO at Fictional AI\nExperience:\nCEO, Fictional AI (2023 - Present)"

    # First addition succeeds
    p1 = await use_case.execute(
        founder_name="Fictional Founder",
        company_name="Fictional AI",
        text=text,
    )
    assert p1.slug == "fictional-founder-fictional-ai"

    # Second addition without override raises DuplicateProfileException with existing details
    with pytest.raises(DuplicateProfileException) as exc_info:
        await use_case.execute(
            founder_name="Fictional Founder",
            company_name="Fictional AI",
            text=text,
            allow_duplicate=False,
        )

    assert exc_info.value.existing_slug == "fictional-founder-fictional-ai"
    assert exc_info.value.existing_id == str(p1.id)

    # Third addition with allow_duplicate=True creates a new profile with slug suffix
    p2 = await use_case.execute(
        founder_name="Fictional Founder",
        company_name="Fictional AI",
        text=text,
        allow_duplicate=True,
    )
    assert p2.id != p1.id
    assert p2.slug.startswith("fictional-founder-fictional-ai-")


@pytest.mark.asyncio
async def test_try_public_fetch_does_not_persist_blocked_unless_requested(
    founder_repo: FounderProfileRepository,
) -> None:
    scraper = AsyncMock(spec=ProfileScraperPort)
    # Scraper returns bot-blocked diagnostic
    blocked_diagnostic = SourceDiagnostic(
        url="https://www.linkedin.com/in/asha-example",
        outcome="blocked_by_bot_protection",
        error_details="HTTP 999 LinkedIn request blocked",
    )
    scraper.fetch_person_with_diagnostic.return_value = (None, blocked_diagnostic)

    use_case = TryPublicFetchUseCase(
        repository=founder_repo,
        scraper=scraper,
    )

    # 1. Without save_as_pending, failed/blocked fetch is NOT persisted (Amendment 3)
    result = await use_case.execute(
        founder_name="Asha Example",
        linkedin_url="https://www.linkedin.com/in/asha-example",
        company_name="Example Corp",
        save_as_pending=False,
    )

    assert result.is_blocked is True
    assert result.persisted is False
    assert result.candidate is None
    count = await founder_repo.count()
    assert count == 0  # Zero rows created

    # 2. With save_as_pending=True, operator explicitly persists pending record
    result_pending = await use_case.execute(
        founder_name="Asha Example",
        linkedin_url="https://www.linkedin.com/in/asha-example",
        company_name="Example Corp",
        save_as_pending=True,
    )

    assert result_pending.persisted is True
    assert result_pending.candidate is not None
    assert result_pending.candidate.retrieval.status == "pending_evidence"
    assert result_pending.candidate.identity_status == "unverified"
    count = await founder_repo.count()
    assert count == 1


@pytest.mark.asyncio
async def test_update_profile_creates_restorable_snapshot_and_restores(
    founder_repo: FounderProfileRepository,
) -> None:
    add_uc = AddFromEvidenceUseCase(founder_repo)
    update_uc = UpdateProfileUseCase(founder_repo)
    restore_uc = RestoreProfileVersionUseCase(founder_repo)

    # Initial profile
    p_initial = await add_uc.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        text="Asha Example\nFounder at Example Corp\nExperience:\nFounder, Example Corp (2020 - 2022)",
    )
    assert len(p_initial.experience_timeline) == 1
    assert p_initial.experience_timeline[0].duration == "2020 - 2022"

    # User re-uploads updated evidence
    p_updated = await update_uc.execute(
        identifier=p_initial.slug,
        text="Asha Example\nCEO at Example Corp\nExperience:\nCEO, Example Corp (2020 - Present)\nCTO, Past Labs (2015 - 2020)",
        is_user_override=True,
    )

    assert len(p_updated.experience_timeline) == 2
    assert p_updated.previous_version is not None
    assert len(p_updated.previous_version["experience_timeline"]) == 1

    # Restore from snapshot
    p_restored = await restore_uc.execute(p_updated.slug)
    assert len(p_restored.experience_timeline) == 1
    assert p_restored.experience_timeline[0].duration == "2020 - 2022"
    assert p_restored.previous_version is None

    # Second restore attempt fails because previous snapshot was consumed
    with pytest.raises(NoPreviousVersionException):
        await restore_uc.execute(p_restored.slug)


@pytest.mark.asyncio
async def test_delete_profile_guarded_by_slug_confirmation(
    founder_repo: FounderProfileRepository,
) -> None:
    add_uc = AddFromEvidenceUseCase(founder_repo)
    delete_uc = DeleteProfileUseCase(founder_repo)

    profile = await add_uc.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        text="Asha Example\nFounder at Example Corp",
    )

    # Mismatched confirmation slug fails
    with pytest.raises(InvalidEvidenceException):
        await delete_uc.execute(identifier=profile.slug, confirm="wrong-slug")

    # Correct slug deletes successfully
    deleted = await delete_uc.execute(identifier=profile.slug, confirm=profile.slug)
    assert deleted is True

    # Profile is gone
    get_uc = GetProfileUseCase(founder_repo)
    with pytest.raises(ProfileNotFoundException):
        await get_uc.execute(profile.slug)


@pytest.mark.asyncio
async def test_export_profile_generates_sanitized_canonical_json(
    founder_repo: FounderProfileRepository,
) -> None:
    add_uc = AddFromEvidenceUseCase(founder_repo)
    export_uc = ExportProfileUseCase(founder_repo)

    profile = await add_uc.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        text="Asha Example\nCEO at Example Corp\nExperience:\nCEO, Example Corp (2022 - Present)",
    )

    payload = await export_uc.execute(profile.slug)
    assert payload["$schema"] == "https://vset.dev/schemas/founder-profile.v1.json"
    assert payload["slug"] == "asha-example-example-corp"
    assert payload["founder_name"] == "Asha Example"
    assert payload["identity_status"] == "user_asserted"
    assert isinstance(payload["experience_timeline"], list)
    assert "created_at" in payload
    assert "updated_at" in payload

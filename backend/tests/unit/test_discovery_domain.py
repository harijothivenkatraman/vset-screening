"""Tests for discovery domain entities."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.entities.discovery import (
    DiscoveryJob,
    JobState,
    SourceCandidate,
    SearchResult,
    CompanyProfile,
    PersonProfile,
    PageContent,
    Evidence,
    EvidenceSource,
    generate_content_fingerprint,
    generate_source_id,
    generate_screen_id,
)
from app.domain.exceptions import (
    DiscoveryError,
    SearchUnavailableError,
    SourceUnavailableError,
    JobNotFoundError,
    DiscoveryDisabledError,
    LlmUnavailableError,
    ExtractionFailedError,
    RateLimitExceededError,
    InsufficientDiskSpaceError,
)


class TestJobState:
    def test_valid_transition_queued_to_running(self) -> None:
        job = _make_job(state=JobState.QUEUED)
        job.transition_to(JobState.RUNNING)
        assert job.state == JobState.RUNNING

    def test_valid_transition_running_to_succeeded(self) -> None:
        job = _make_job(state=JobState.RUNNING)
        job.transition_to(JobState.SUCCEEDED)
        assert job.state == JobState.SUCCEEDED

    def test_valid_transition_running_to_partial(self) -> None:
        job = _make_job(state=JobState.RUNNING)
        job.transition_to(JobState.PARTIAL)
        assert job.state == JobState.PARTIAL

    def test_valid_transition_running_to_failed(self) -> None:
        job = _make_job(state=JobState.RUNNING)
        job.transition_to(JobState.FAILED)
        assert job.state == JobState.FAILED

    def test_invalid_transition_queued_to_succeeded(self) -> None:
        job = _make_job(state=JobState.QUEUED)
        with pytest.raises(ValueError, match="Invalid state transition"):
            job.transition_to(JobState.SUCCEEDED)

    def test_invalid_transition_queued_to_failed(self) -> None:
        job = _make_job(state=JobState.QUEUED)
        with pytest.raises(ValueError, match="Invalid state transition"):
            job.transition_to(JobState.FAILED)

    def test_invalid_transition_succeeded_to_running(self) -> None:
        job = _make_job(state=JobState.SUCCEEDED)
        with pytest.raises(ValueError, match="Invalid state transition"):
            job.transition_to(JobState.RUNNING)


class TestDiscoveryJob:
    def test_update_progress(self) -> None:
        job = _make_job()
        job.update_progress("Scraping", 0.5)
        assert job.stage == "Scraping"
        assert job.progress == 0.5

    def test_progress_clamped(self) -> None:
        job = _make_job()
        job.update_progress("Testing", 1.5)
        assert job.progress == 1.0
        job.update_progress("Testing", -0.5)
        assert job.progress == 0.0

    def test_add_warning(self) -> None:
        job = _make_job()
        assert len(job.warnings) == 0
        job.add_warning("LinkedIn auth-walled")
        assert len(job.warnings) == 1
        assert job.warnings[0] == "LinkedIn auth-walled"


class TestHelpers:
    def test_generate_content_fingerprint_deterministic(self) -> None:
        fp1 = generate_content_fingerprint("hello")
        fp2 = generate_content_fingerprint("hello")
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256 hex

    def test_generate_content_fingerprint_different_for_different_content(self) -> None:
        fp1 = generate_content_fingerprint("hello")
        fp2 = generate_content_fingerprint("world")
        assert fp1 != fp2

    def test_generate_source_id(self) -> None:
        sid = generate_source_id("https://linkedin.com/company/acme")
        assert sid.startswith("src_")
        assert len(sid) == 16  # "src_" + 12 hex chars

    def test_generate_source_id_deterministic(self) -> None:
        sid1 = generate_source_id("https://example.com")
        sid2 = generate_source_id("https://example.com")
        assert sid1 == sid2

    def test_generate_screen_id(self) -> None:
        sid = generate_screen_id("Acme Corp")
        assert sid.startswith("cs_")
        assert len(sid) == 27  # "cs_" + 24 hex chars

    def test_generate_screen_id_case_insensitive(self) -> None:
        sid1 = generate_screen_id("Acme Corp")
        sid2 = generate_screen_id("acme corp")
        assert sid1 == sid2


class TestFrozenEntities:
    def test_search_result_is_frozen(self) -> None:
        r = SearchResult(url="https://x.com", title="X", snippet="s", domain="x.com")
        with pytest.raises(AttributeError):
            r.url = "changed"  # type: ignore[misc]

    def test_source_candidate_is_frozen(self) -> None:
        c = SourceCandidate(
            url="u", title="t", snippet="s", domain="d",
            confidence=0.9, category="company_linkedin",
            search_query="q", entity_name="e",
        )
        with pytest.raises(AttributeError):
            c.confidence = 0.1  # type: ignore[misc]

    def test_company_profile_is_frozen(self) -> None:
        p = CompanyProfile(name="Acme")
        with pytest.raises(AttributeError):
            p.name = "Changed"  # type: ignore[misc]


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_discovery_error(self) -> None:
        exceptions = [
            SearchUnavailableError(["duckduckgo"]),
            SourceUnavailableError("http://x.com", "timeout"),
            JobNotFoundError("abc"),
            DiscoveryDisabledError(),
            LlmUnavailableError("http://localhost:11434"),
            ExtractionFailedError("company", "parse error"),
            RateLimitExceededError(5),
            InsufficientDiskSpaceError(1.5, 2.0),
        ]
        for exc in exceptions:
            assert isinstance(exc, DiscoveryError)
            assert isinstance(exc, Exception)
            assert exc.message  # all have a message

    def test_search_unavailable_includes_providers(self) -> None:
        exc = SearchUnavailableError(["searxng", "duckduckgo"])
        assert "searxng" in exc.message
        assert "duckduckgo" in exc.message
        assert exc.providers_tried == ["searxng", "duckduckgo"]


# ── Helpers ────────────────────────────────────────────────────────────

def _make_job(state: JobState = JobState.QUEUED) -> DiscoveryJob:
    now = datetime.now(timezone.utc)
    return DiscoveryJob(
        id="test-job-1",
        company_name="TestCo",
        founder_names=["Alice", "Bob"],
        state=state,
        stage="Initial",
        progress=0.0,
        warnings=[],
        result_slug=None,
        created_at=now,
        updated_at=now,
        confirmed_urls={},
    )

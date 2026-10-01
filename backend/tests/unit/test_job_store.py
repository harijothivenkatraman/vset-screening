"""Unit tests for InMemoryJobStore."""
from __future__ import annotations

import datetime
import pytest

from app.domain.entities.discovery import DiscoveryJob, JobState
from app.infrastructure.discovery.jobs.in_memory_job_store import InMemoryJobStore


def _make_job(job_id: str, minutes_ago: int = 0) -> DiscoveryJob:
    now = datetime.datetime.now(datetime.timezone.utc)
    created = now - datetime.timedelta(minutes=minutes_ago)
    return DiscoveryJob(
        id=job_id,
        company_name=f"Company-{job_id}",
        founder_names=["Alice"],
        state=JobState.QUEUED,
        stage="init",
        progress=0.0,
        warnings=[],
        result_slug=None,
        created_at=created,
        updated_at=created,
        confirmed_urls={},
    )


class TestInMemoryJobStore:
    async def test_create_and_get(self) -> None:
        store = InMemoryJobStore(max_jobs=10)
        job = _make_job("j1")
        await store.create(job)
        retrieved = await store.get("j1")
        assert retrieved is not None
        assert retrieved.id == "j1"

    async def test_update(self) -> None:
        store = InMemoryJobStore(max_jobs=10)
        job = _make_job("j2")
        await store.create(job)
        job.update_progress("running", 0.5)
        await store.update(job)
        updated = await store.get("j2")
        assert updated is not None
        assert updated.progress == 0.5
        assert updated.stage == "running"

    async def test_list_recent(self) -> None:
        store = InMemoryJobStore(max_jobs=10)
        j1 = _make_job("j1", minutes_ago=10)
        j2 = _make_job("j2", minutes_ago=5)
        j3 = _make_job("j3", minutes_ago=1)
        await store.create(j1)
        await store.create(j2)
        await store.create(j3)

        recent = await store.list_recent(limit=2)
        assert len(recent) == 2
        assert recent[0].id == "j3"  # newest first
        assert recent[1].id == "j2"

    async def test_capacity_eviction(self) -> None:
        store = InMemoryJobStore(max_jobs=2)
        j1 = _make_job("j1", minutes_ago=20)
        j2 = _make_job("j2", minutes_ago=10)
        await store.create(j1)
        await store.create(j2)
        j3 = _make_job("j3", minutes_ago=0)
        await store.create(j3)  # should evict oldest (j1)

        assert await store.get("j1") is None
        assert await store.get("j2") is not None
        assert await store.get("j3") is not None

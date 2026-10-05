"""Use case: List founder profiles with search, status filtering, and pagination."""
from __future__ import annotations

from dataclasses import dataclass
from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import FounderProfile


@dataclass(frozen=True)
class ListProfilesResult:
    items: list[FounderProfile]
    total: int
    limit: int
    offset: int


class ListProfilesUseCase:
    """Lists profiles ordered by updated_at descending."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ListProfilesResult:
        search_clean = search.strip() if search else None
        status_clean = status.strip() if status else None

        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        items = await self._repository.list_all(
            search=search_clean,
            status=status_clean,
            limit=safe_limit,
            offset=safe_offset,
        )
        total = await self._repository.count(
            search=search_clean,
            status=status_clean,
        )

        return ListProfilesResult(
            items=items,
            total=total,
            limit=safe_limit,
            offset=safe_offset,
        )

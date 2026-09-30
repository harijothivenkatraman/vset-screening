from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.get_sources import GetSourcesService
from app.presentation.dependencies import get_sources_service
from app.presentation.schemas.source_schemas import (
    SourceItemResponse,
    SourcesResponse,
)

router = APIRouter(prefix="/companies/{slug}/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse)
async def get_sources(
    slug: str,
    service: GetSourcesService = Depends(get_sources_service),
) -> SourcesResponse:
    sources_data = await service.execute(slug)
    if sources_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with slug '{slug}' not found",
        )

    return SourcesResponse(
        aboutText=sources_data.about_text,
        limitations=sources_data.limitations,
        researchWindow=sources_data.research_window,
        sources=[
            SourceItemResponse(
                sourceId=s["sourceId"],
                position=s["position"],
                title=s["title"],
                publisher=s.get("publisher"),
                publishedDate=s.get("publishedDate"),
                displayUrl=s.get("displayUrl"),
                canonicalUrl=s.get("canonicalUrl"),
            )
            for s in sources_data.sources
        ],
    )

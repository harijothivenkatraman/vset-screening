from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.get_section import GetSectionService
from app.application.services.get_section_nav import GetSectionNavService
from app.presentation.dependencies import (
    get_section_nav_service,
    get_section_service,
)
from app.presentation.schemas.section_schemas import (
    InfoToPrepareItem,
    SectionDetailResponse,
    SectionNavItemResponse,
    SectionNavListResponse,
)

router = APIRouter(prefix="/companies/{slug}/sections", tags=["sections"])


@router.get("", response_model=SectionNavListResponse)
async def get_sections_nav(
    slug: str,
    service: GetSectionNavService = Depends(get_section_nav_service),
) -> SectionNavListResponse:
    nav_items = await service.execute(slug)
    if nav_items is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with slug '{slug}' not found",
        )
    return SectionNavListResponse(
        sections=[
            SectionNavItemResponse(
                key=item.key,
                title=item.title,
                position=item.position,
            )
            for item in nav_items
        ]
    )


@router.get("/{key}", response_model=SectionDetailResponse)
async def get_section_detail(
    slug: str,
    key: str,
    service: GetSectionService = Depends(get_section_service),
) -> SectionDetailResponse:
    section = await service.execute(slug, key)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{key}' not found for company '{slug}'",
        )
    return SectionDetailResponse(
        key=section.key,
        title=section.title,
        position=section.position,
        ribbon=section.ribbon,
        blocks=section.blocks,
        informationToPrepare=[
            InfoToPrepareItem(
                id=item["id"],
                text=item["text"],
                why=item.get("why"),
            )
            for item in section.information_to_prepare
        ],
    )

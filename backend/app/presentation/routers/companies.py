import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.delete_company import DeleteCompanyService
from app.application.services.get_report_header import GetReportHeaderService
from app.application.services.list_companies import ListCompaniesService
from app.presentation.dependencies import (
    get_delete_company_service,
    get_list_companies_service,
    get_report_header_service,
)
from app.presentation.guards.api_key_guard import verify_admin_key, verify_read_or_admin_key
from app.presentation.schemas.company_schemas import (
    CompaniesListResponse,
    CompanyListItemResponse,
    ReportHeaderResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompaniesListResponse, dependencies=[Depends(verify_read_or_admin_key)])
async def list_companies(
    service: ListCompaniesService = Depends(get_list_companies_service),
) -> CompaniesListResponse:
    results = await service.execute()
    return CompaniesListResponse(
        companies=[
            CompanyListItemResponse(
                slug=c.slug,
                name=c.name,
                website=c.website,
                audienceLabel=c.audience_label,
                stage=c.stage,
                sector=c.sector,
            )
            for c in results
        ]
    )


@router.get("/{slug}", response_model=ReportHeaderResponse, dependencies=[Depends(verify_read_or_admin_key)])
async def get_report_header(
    slug: str,
    service: GetReportHeaderService = Depends(get_report_header_service),
) -> ReportHeaderResponse:
    header = await service.execute(slug)
    if header is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with slug '{slug}' not found",
        )
    return ReportHeaderResponse(
        slug=header.slug,
        name=header.name,
        cover=header.cover,
        ribbon=header.ribbon,
        audienceLabel=header.audience_label,
        asOfDate=header.as_of_date,
        generatedAt=header.generated_at,
        presentation=header.presentation,
    )


@router.delete(
    "/{slug}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def delete_company(
    slug: str,
    confirm: str = Query(..., description="Must match the company slug to confirm deletion"),
    service: DeleteCompanyService = Depends(get_delete_company_service),
) -> dict[str, Any]:
    if confirm != slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation query parameter 'confirm' must match company slug '{slug}'.",
        )
    deleted = await service.execute(slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with slug '{slug}' not found",
        )
    logger.info("Deleted company slug=%s timestamp=%s", slug, datetime.now(timezone.utc).isoformat())
    return {
        "deleted": True,
        "slug": slug,
        "message": f"Company '{slug}' and all associated reports, sections, sources, and snapshots deleted successfully.",
    }

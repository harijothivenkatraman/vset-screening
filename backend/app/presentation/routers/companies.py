from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.get_report_header import GetReportHeaderService
from app.application.services.list_companies import ListCompaniesService
from app.presentation.dependencies import (
    get_list_companies_service,
    get_report_header_service,
)
from app.presentation.schemas.company_schemas import (
    CompaniesListResponse,
    CompanyListItemResponse,
    ReportHeaderResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompaniesListResponse)
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


@router.get("/{slug}", response_model=ReportHeaderResponse)
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

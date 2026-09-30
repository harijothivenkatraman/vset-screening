from typing import Any
from pydantic import BaseModel


class CompanyListItemResponse(BaseModel):
    slug: str
    name: str
    website: str | None = None
    audienceLabel: str
    stage: str | None = None
    sector: str | None = None


class CompaniesListResponse(BaseModel):
    companies: list[CompanyListItemResponse]


class CoverResponse(BaseModel):
    company_name: str | None = None
    report_reference: str | None = None
    research_cutoff: str | None = None
    website: str | None = None

    model_config = {"extra": "allow"}


class ReportHeaderResponse(BaseModel):
    slug: str
    name: str
    cover: dict[str, Any]
    ribbon: list[Any]
    audienceLabel: str
    asOfDate: str | None = None
    generatedAt: str | None = None
    presentation: dict[str, Any]

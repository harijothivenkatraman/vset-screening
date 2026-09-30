from typing import Any

from pydantic import BaseModel, Field, ValidationError


class CanonicalMetaValidator(BaseModel):
    canonical_screen_id: str = Field(min_length=1)
    canonical_version: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    final_fingerprint: str = Field(min_length=1)
    website: str | None = None
    report_id: str | None = None
    research_cutoff: str | None = None
    generated_at: str | None = None
    version: str | None = None

    model_config = {"extra": "allow"}


class CoverValidator(BaseModel):
    company_name: str = Field(min_length=1)
    report_reference: str | None = None
    research_cutoff: str | None = None
    website: str | None = None

    model_config = {"extra": "allow"}


class SectionValidator(BaseModel):
    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    ribbon: list[Any] = Field(default_factory=list)
    blocks: list[Any] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class FinalMetaValidator(BaseModel):
    schema_version: str = Field(min_length=1)
    final_fingerprint: str | None = None
    as_of_date: str | None = None

    model_config = {"extra": "allow"}


class FinalValidator(BaseModel):
    meta: FinalMetaValidator

    model_config = {"extra": "allow"}


class ContentValidator(BaseModel):
    cover: CoverValidator
    sections: list[SectionValidator]
    final: FinalValidator

    model_config = {"extra": "allow"}


class CanonicalValidator(BaseModel):
    meta: CanonicalMetaValidator
    content: ContentValidator

    model_config = {"extra": "allow"}


class RawReportValidator(BaseModel):
    canonical: CanonicalValidator

    model_config = {"extra": "allow"}


def validate_raw_report_json(raw_data: dict[str, Any]) -> RawReportValidator:
    try:
        return RawReportValidator.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"Schema validation error: {e}") from e

from typing import Any
from pydantic import BaseModel


class SectionNavItemResponse(BaseModel):
    key: str
    title: str
    position: int


class SectionNavListResponse(BaseModel):
    sections: list[SectionNavItemResponse]


class InfoToPrepareItem(BaseModel):
    id: str | None = None
    text: str
    why: str | None = None


class SectionDetailResponse(BaseModel):
    key: str
    title: str
    position: int
    ribbon: list[Any]
    blocks: list[Any]
    informationToPrepare: list[InfoToPrepareItem]

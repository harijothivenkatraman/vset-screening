from typing import Any
from pydantic import BaseModel


class SourceItemResponse(BaseModel):
    sourceId: str
    position: int
    title: str
    publisher: str | None = None
    publishedDate: str | None = None
    displayUrl: str | None = None
    canonicalUrl: str | None = None


class SourcesResponse(BaseModel):
    aboutText: str
    limitations: list[str] = []
    researchWindow: dict[str, Any] = {}
    sources: list[SourceItemResponse]

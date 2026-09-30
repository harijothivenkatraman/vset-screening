from pydantic import BaseModel


class ImportResponse(BaseModel):
    status: str  # "created" | "updated" | "unchanged"
    company_slug: str
    message: str

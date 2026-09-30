from typing import Any
from pydantic import BaseModel


class ConcernsResponse(BaseModel):
    concerns: list[Any] = []
    conflicts: list[Any] = []
    message: str = ""


class ActionPresentationResponse(BaseModel):
    actionIntro: str = ""
    partATitle: str = "A. Questions to prepare for"
    partBTitle: str = "B. Supporting documents & data to prepare"
    actionSectionTitle: str = "Investor questions & information to prepare"


class QuestionItemResponse(BaseModel):
    id: str
    text: str
    why: str | None = None


class TopicQuestionsResponse(BaseModel):
    topic: str
    items: list[QuestionItemResponse]


class DocumentGroupResponse(BaseModel):
    group: str
    priority: list[str] = []
    secondary: list[str] = []


class ActionsResponse(BaseModel):
    concerns: ConcernsResponse
    presentation: ActionPresentationResponse
    questions: list[TopicQuestionsResponse]
    documents: list[DocumentGroupResponse]

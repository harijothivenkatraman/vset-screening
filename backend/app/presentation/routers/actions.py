from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.get_actions import GetActionsService
from app.presentation.dependencies import get_actions_service
from app.presentation.guards.api_key_guard import verify_read_or_admin_key
from app.presentation.schemas.action_schemas import (
    ActionPresentationResponse,
    ActionsResponse,
    ConcernsResponse,
    DocumentGroupResponse,
    QuestionItemResponse,
    TopicQuestionsResponse,
)

router = APIRouter(prefix="/companies/{slug}/actions", tags=["actions"])


@router.get("", response_model=ActionsResponse, dependencies=[Depends(verify_read_or_admin_key)])
async def get_actions(
    slug: str,
    service: GetActionsService = Depends(get_actions_service),
) -> ActionsResponse:
    actions_data = await service.execute(slug)
    if actions_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with slug '{slug}' not found",
        )

    return ActionsResponse(
        concerns=ConcernsResponse(
            concerns=actions_data.concerns.get("concerns", []),
            conflicts=actions_data.concerns.get("conflicts", []),
            message=actions_data.concerns.get("message", ""),
        ),
        presentation=ActionPresentationResponse(
            actionIntro=actions_data.presentation.get("actionIntro", ""),
            partATitle=actions_data.presentation.get("partATitle", "A. Questions to prepare for"),
            partBTitle=actions_data.presentation.get("partBTitle", "B. Supporting documents & data to prepare"),
            actionSectionTitle=actions_data.presentation.get(
                "actionSectionTitle", "Investor questions & information to prepare"
            ),
        ),
        questions=[
            TopicQuestionsResponse(
                topic=t["topic"],
                items=[
                    QuestionItemResponse(
                        id=q["id"],
                        text=q["text"],
                        why=q.get("why"),
                    )
                    for q in t["items"]
                ],
            )
            for t in actions_data.questions
        ],
        documents=[
            DocumentGroupResponse(
                group=d["group"],
                priority=d.get("priority", []),
                secondary=d.get("secondary", []),
            )
            for d in actions_data.documents
        ],
    )

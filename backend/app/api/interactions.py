from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.interactions import (
    ChatRequest,
    CompareAnswerRead,
    CompareRequest,
    ExplainRequest,
    GroundedAnswerRead,
    WhyAnswerRead,
)
from app.services.ai.factory import create_provider
from app.services.ai.settings import AISettingsService
from app.services.interactions import InteractionService

router = APIRouter(tags=["AI interactions"])


def interaction_service(db: DbSession, user: CurrentUser) -> InteractionService:
    setting = AISettingsService(db, user.id).require()
    return InteractionService(db, user.id, create_provider(setting))


@router.post("/concepts/{concept_id}/explain", response_model=ApiResponse[GroundedAnswerRead])
def explain_concept(
    concept_id: UUID,
    payload: ExplainRequest,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[GroundedAnswerRead]:
    return ApiResponse(data=interaction_service(db, user).explain(concept_id, payload.mode))


@router.post("/concepts/{concept_id}/why", response_model=ApiResponse[WhyAnswerRead])
def explain_why(concept_id: UUID, user: CurrentUser, db: DbSession) -> ApiResponse[WhyAnswerRead]:
    return ApiResponse(data=interaction_service(db, user).why(concept_id))


@router.post(
    "/workspaces/{workspace_id}/compare",
    response_model=ApiResponse[CompareAnswerRead],
)
def compare_concepts(
    workspace_id: UUID,
    payload: CompareRequest,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[CompareAnswerRead]:
    service = interaction_service(db, user)
    return ApiResponse(
        data=service.compare(workspace_id, payload.concept_a_id, payload.concept_b_id)
    )


@router.post(
    "/workspaces/{workspace_id}/chat",
    response_model=ApiResponse[GroundedAnswerRead],
)
def chat_with_graph(
    workspace_id: UUID,
    payload: ChatRequest,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[GroundedAnswerRead]:
    return ApiResponse(data=interaction_service(db, user).chat(workspace_id, payload.question))

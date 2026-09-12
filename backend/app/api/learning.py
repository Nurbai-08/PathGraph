from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.learning import (
    KnowledgeStateUpdate,
    LearningPathCreate,
    LearningPathRead,
    NextConceptRead,
    QuizAnswer,
    QuizQuestionRead,
    QuizResultRead,
)
from app.services.ai.factory import create_provider
from app.services.ai.settings import AISettingsService
from app.services.learning import LearningPathService
from app.services.quizzes import QuizService

router = APIRouter(tags=["learning"])


@router.post(
    "/workspaces/{workspace_id}/learning-paths",
    response_model=ApiResponse[LearningPathRead],
    status_code=status.HTTP_201_CREATED,
)
def create_learning_path(
    workspace_id: UUID,
    payload: LearningPathCreate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[LearningPathRead]:
    return ApiResponse(data=LearningPathService(db, user.id).create(workspace_id, payload))


@router.get(
    "/workspaces/{workspace_id}/learning-paths",
    response_model=ApiResponse[list[LearningPathRead]],
)
def list_learning_paths(
    workspace_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[list[LearningPathRead]]:
    return ApiResponse(data=LearningPathService(db, user.id).list(workspace_id))


@router.get("/learning-paths/{path_id}", response_model=ApiResponse[LearningPathRead])
def get_learning_path(
    path_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[LearningPathRead]:
    return ApiResponse(data=LearningPathService(db, user.id).get(path_id))


@router.get("/learning-paths/{path_id}/next", response_model=ApiResponse[NextConceptRead])
def get_next_concept(
    path_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[NextConceptRead]:
    return ApiResponse(data=LearningPathService(db, user.id).next_concept(path_id))


@router.get("/concepts/{concept_id}/quiz", response_model=ApiResponse[list[QuizQuestionRead]])
def list_quiz_questions(
    concept_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[list[QuizQuestionRead]]:
    return ApiResponse(data=QuizService(db, user.id).list_for_concept(concept_id))


@router.post("/concepts/{concept_id}/quiz", response_model=ApiResponse[list[QuizQuestionRead]])
def generate_quiz(
    concept_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[list[QuizQuestionRead]]:
    setting = AISettingsService(db, user.id).require()
    questions = QuizService(db, user.id).generate(concept_id, create_provider(setting))
    return ApiResponse(data=questions)


@router.post("/quiz-questions/{question_id}/answer", response_model=ApiResponse[QuizResultRead])
def answer_quiz_question(
    question_id: UUID,
    payload: QuizAnswer,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[QuizResultRead]:
    return ApiResponse(data=QuizService(db, user.id).answer(question_id, payload.answer))


@router.patch("/concepts/{concept_id}/knowledge", response_model=ApiResponse[dict[str, object]])
def update_knowledge_state(
    concept_id: UUID,
    payload: KnowledgeStateUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[dict[str, object]]:
    state = QuizService(db, user.id).set_manual_status(concept_id, payload.status)
    return ApiResponse(
        data={"concept_id": state.concept_id, "status": state.status, "mastery": state.mastery}
    )

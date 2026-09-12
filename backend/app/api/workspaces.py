from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services.workspaces import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=ApiResponse[WorkspaceRead], status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[WorkspaceRead]:
    workspace = WorkspaceService(db, user.id).create(payload)
    return ApiResponse(data=WorkspaceRead.model_validate(workspace))


@router.get("", response_model=ApiResponse[list[WorkspaceRead]])
def list_workspaces(user: CurrentUser, db: DbSession) -> ApiResponse[list[WorkspaceRead]]:
    workspaces = WorkspaceService(db, user.id).list()
    return ApiResponse(data=[WorkspaceRead.model_validate(item) for item in workspaces])


@router.get("/{workspace_id}", response_model=ApiResponse[WorkspaceRead])
def get_workspace(
    workspace_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[WorkspaceRead]:
    workspace = WorkspaceService(db, user.id).get(workspace_id)
    return ApiResponse(data=WorkspaceRead.model_validate(workspace))


@router.patch("/{workspace_id}", response_model=ApiResponse[WorkspaceRead])
def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[WorkspaceRead]:
    workspace = WorkspaceService(db, user.id).update(workspace_id, payload)
    return ApiResponse(data=WorkspaceRead.model_validate(workspace))


@router.delete("/{workspace_id}", response_model=ApiResponse[dict[str, bool]])
def delete_workspace(
    workspace_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[dict[str, bool]]:
    WorkspaceService(db, user.id).delete(workspace_id)
    return ApiResponse(data={"deleted": True})

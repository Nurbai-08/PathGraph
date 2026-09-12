from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.errors import AppError
from app.models.source import ProcessingJob, Source
from app.models.workspace import Workspace
from app.schemas.common import ApiResponse
from app.schemas.source import ProcessingJobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ApiResponse[ProcessingJobRead])
def get_job(job_id: UUID, user: CurrentUser, db: DbSession) -> ApiResponse[ProcessingJobRead]:
    job = db.scalar(
        select(ProcessingJob)
        .join(Source)
        .join(Workspace)
        .where(ProcessingJob.id == job_id, Workspace.user_id == user.id)
    )
    if not job:
        raise AppError(404, "JOB_NOT_FOUND", "Processing job was not found.")
    return ApiResponse(data=ProcessingJobRead.model_validate(job))

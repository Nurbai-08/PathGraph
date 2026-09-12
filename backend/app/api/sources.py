from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import settings
from app.core.errors import AppError
from app.models.source import ProcessingJob, Source
from app.schemas.common import ApiResponse
from app.schemas.source import DocumentRead, ProcessingJobRead, SourceDetail, SourceRead
from app.services.ai.settings import AISettingsService
from app.services.source_processing import process_source_task
from app.services.sources import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=ApiResponse[SourceRead], status_code=status.HTTP_201_CREATED)
async def create_source(
    background_tasks: BackgroundTasks,
    workspace_id: Annotated[UUID, Form()],
    source_type: Annotated[str, Form(alias="type")],
    user: CurrentUser,
    db: DbSession,
    title: Annotated[str | None, Form()] = None,
    url: Annotated[str | None, Form()] = None,
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> ApiResponse[SourceRead]:
    file_content = await file.read(settings.source_max_bytes + 1) if file else None
    source, job = SourceService(db, user.id).create(
        workspace_id, source_type, title, url, text, file_content
    )
    response = source_response(source, job)
    background_tasks.add_task(process_source_task, source.id, job.id)
    return ApiResponse(data=response)


@router.get("", response_model=ApiResponse[list[SourceRead]])
def list_sources(
    workspace_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[list[SourceRead]]:
    service = SourceService(db, user.id)
    sources = service.list(workspace_id)
    return ApiResponse(
        data=[source_response(source, service.latest_job(source.id)) for source in sources]
    )


@router.get("/{source_id}", response_model=ApiResponse[SourceDetail])
def get_source(source_id: UUID, user: CurrentUser, db: DbSession) -> ApiResponse[SourceDetail]:
    service = SourceService(db, user.id)
    source = service.get(source_id)
    document = service.latest_document(source.id)
    data = SourceDetail(
        **source_response(source, service.latest_job(source.id)).model_dump(),
        document=DocumentRead.model_validate(document) if document else None,
    )
    return ApiResponse(data=data)


@router.delete("/{source_id}", response_model=ApiResponse[dict[str, bool]])
def delete_source(
    source_id: UUID, user: CurrentUser, db: DbSession
) -> ApiResponse[dict[str, bool]]:
    SourceService(db, user.id).delete(source_id)
    return ApiResponse(data={"deleted": True})


@router.post("/{source_id}/process", response_model=ApiResponse[ProcessingJobRead])
def process_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[ProcessingJobRead]:
    job = SourceService(db, user.id).create_processing_job(source_id)
    background_tasks.add_task(process_source_task, source_id, job.id)
    return ApiResponse(data=ProcessingJobRead.model_validate(job))


@router.post("/{source_id}/retry", response_model=ApiResponse[ProcessingJobRead])
def retry_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[ProcessingJobRead]:
    job = SourceService(db, user.id).retry_job(source_id)
    background_tasks.add_task(process_source_task, source_id, job.id)
    return ApiResponse(data=ProcessingJobRead.model_validate(job))


@router.post("/{source_id}/analyze", response_model=ApiResponse[dict[str, bool]])
def analyze_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[dict[str, bool]]:
    service = SourceService(db, user.id)
    source = service.get(source_id)
    if source.status != "ready":
        raise AppError(409, "SOURCE_NOT_READY", "The source must be ready before analysis.")
    AISettingsService(db, user.id).require()
    job = service.create_processing_job(source_id)
    job.stage = "analyzing"
    db.commit()
    background_tasks.add_task(process_source_task, source_id, job.id)
    return ApiResponse(data={"queued": True})


def source_response(source: Source, job: ProcessingJob | None) -> SourceRead:
    return SourceRead(
        id=source.id,
        workspace_id=source.workspace_id,
        type=source.type,
        url=source.url,
        title=source.title,
        status=source.status,
        content_hash=source.content_hash,
        language=source.language,
        created_at=source.created_at,
        updated_at=source.updated_at,
        job=ProcessingJobRead.model_validate(job) if job else None,
    )

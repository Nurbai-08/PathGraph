from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

SourceType = Literal["url", "pdf", "text"]
SourceStatus = Literal["pending", "processing", "ready", "failed"]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
JobStage = Literal["fetching", "extracting", "cleaning", "chunking", "saving", "analyzing"]


class ProcessingJobRead(BaseModel):
    id: UUID
    source_id: UUID
    status: JobStatus
    stage: JobStage
    progress: int
    attempt_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceRead(BaseModel):
    id: UUID
    workspace_id: UUID
    type: SourceType
    url: str | None
    title: str
    status: SourceStatus
    content_hash: str | None
    language: str | None
    created_at: datetime
    updated_at: datetime
    job: ProcessingJobRead | None = None


class ChunkRead(BaseModel):
    id: UUID
    position: int
    heading_path: str
    content: str
    token_count: int

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: UUID
    version: int
    clean_content: str
    content_hash: str | None
    word_count: int
    chunks: list[ChunkRead]

    model_config = ConfigDict(from_attributes=True)


class SourceDetail(SourceRead):
    document: DocumentRead | None = None

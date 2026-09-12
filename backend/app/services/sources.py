import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.url_security import normalize_and_validate_url
from app.models.concept import Concept, ConceptSource
from app.models.source import Document, ProcessingJob, Source
from app.models.workspace import Workspace
from app.services.source_content import clean_plain_text, extract_pdf
from app.services.source_storage import SourceStorage


class SourceService:
    def __init__(self, db: Session, user_id: UUID, storage: SourceStorage | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.storage = storage or SourceStorage()

    def create(
        self,
        workspace_id: UUID,
        source_type: str,
        title: str | None,
        url: str | None,
        text: str | None,
        file_content: bytes | None,
    ) -> tuple[Source, ProcessingJob]:
        self._require_workspace(workspace_id)
        canonical_url, payload, content_hash = self._validate_input(
            source_type, url, text, file_content
        )
        self._require_unique(workspace_id, canonical_url, content_hash)

        source = Source(
            workspace_id=workspace_id,
            type=source_type,
            url=canonical_url,
            title=(title or canonical_url or default_source_title(source_type)).strip()[:300],
            content_hash=content_hash,
        )
        job = ProcessingJob(source=source)
        self.db.add_all([source, job])
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise AppError(409, "DUPLICATE_SOURCE", "This source already exists.") from error
        if payload is not None:
            self.storage.save(source.id, payload)
        return source, job

    def list(self, workspace_id: UUID) -> list[Source]:
        self._require_workspace(workspace_id)
        query = (
            select(Source)
            .where(Source.workspace_id == workspace_id)
            .order_by(Source.created_at.desc())
        )
        return list(self.db.scalars(query))

    def get(self, source_id: UUID) -> Source:
        source = self.db.scalar(
            select(Source)
            .join(Workspace)
            .where(Source.id == source_id, Workspace.user_id == self.user_id)
        )
        if not source:
            raise AppError(404, "SOURCE_NOT_FOUND", "Source was not found.")
        return source

    def latest_document(self, source_id: UUID) -> Document | None:
        return self.db.scalar(
            select(Document)
            .where(Document.source_id == source_id)
            .order_by(Document.version.desc())
        )

    def latest_job(self, source_id: UUID) -> ProcessingJob | None:
        return self.db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.source_id == source_id)
            .order_by(ProcessingJob.created_at.desc())
        )

    def create_processing_job(self, source_id: UUID) -> ProcessingJob:
        source = self.get(source_id)
        active_job = self.latest_job(source_id)
        if active_job and active_job.status in {"queued", "running"}:
            raise AppError(409, "JOB_ALREADY_RUNNING", "This source is already being processed.")
        job = ProcessingJob(source_id=source.id)
        source.status = "pending"
        self.db.add(job)
        self.db.commit()
        return job

    def retry_job(self, source_id: UUID) -> ProcessingJob:
        source = self.get(source_id)
        job = self.latest_job(source.id)
        if not job or job.status != "failed":
            raise AppError(409, "JOB_NOT_RETRYABLE", "The latest job cannot be retried.")
        job.status = "queued"
        job.error_code = None
        job.error_message = None
        source.status = "pending"
        self.db.commit()
        return job

    def delete(self, source_id: UUID) -> None:
        source = self.get(source_id)
        concept_ids = set(
            self.db.scalars(
                select(ConceptSource.concept_id).where(ConceptSource.source_id == source_id)
            )
        )
        self.db.delete(source)
        self.db.commit()
        for concept_id in concept_ids:
            concept = self.db.get(Concept, concept_id)
            has_evidence = self.db.scalar(
                select(ConceptSource.id).where(ConceptSource.concept_id == concept_id).limit(1)
            )
            if concept and not concept.is_manual and not has_evidence:
                self.db.delete(concept)
        self.db.commit()
        self.storage.delete(source_id)

    def _require_workspace(self, workspace_id: UUID) -> None:
        exists = self.db.scalar(
            select(Workspace.id).where(
                Workspace.id == workspace_id,
                Workspace.user_id == self.user_id,
            )
        )
        if not exists:
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found.")

    def _validate_input(
        self,
        source_type: str,
        url: str | None,
        text: str | None,
        file_content: bytes | None,
    ) -> tuple[str | None, bytes | None, str | None]:
        if source_type == "url":
            if not url:
                raise AppError(422, "SOURCE_URL_REQUIRED", "A URL is required.")
            return normalize_and_validate_url(url), None, None
        if source_type == "text":
            content = (text or "").encode()
            clean_content = clean_plain_text(text or "")
            if not clean_content:
                raise AppError(422, "SOURCE_TEXT_REQUIRED", "Text content is required.")
            self._require_size(content)
            return None, content, hashlib.sha256(clean_content.encode()).hexdigest()
        if source_type == "pdf":
            content = file_content or b""
            if not content.startswith(b"%PDF-"):
                raise AppError(422, "INVALID_PDF", "A valid PDF file is required.")
            self._require_size(content)
            clean_content = clean_plain_text(extract_pdf(content))
            if not clean_content:
                raise AppError(422, "EMPTY_SOURCE", "No readable text was found in the PDF.")
            return None, content, hashlib.sha256(clean_content.encode()).hexdigest()
        raise AppError(422, "INVALID_SOURCE_TYPE", "Source type must be url, text, or pdf.")

    def _require_size(self, content: bytes) -> None:
        if len(content) > settings.source_max_bytes:
            raise AppError(413, "SOURCE_TOO_LARGE", "The source exceeds the maximum allowed size.")

    def _require_unique(
        self, workspace_id: UUID, canonical_url: str | None, content_hash: str | None
    ) -> None:
        conditions = []
        if canonical_url:
            conditions.append(Source.url == canonical_url)
        if content_hash:
            conditions.append(Source.content_hash == content_hash)
        for condition in conditions:
            duplicate = self.db.scalar(
                select(Source.id).where(Source.workspace_id == workspace_id, condition)
            )
            if duplicate:
                raise AppError(409, "DUPLICATE_SOURCE", "This source already exists.")


def default_source_title(source_type: str) -> str:
    return {"text": "Text source", "pdf": "PDF source", "url": "Web source"}.get(
        source_type, "Untitled source"
    )

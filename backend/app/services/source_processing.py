import hashlib
from datetime import UTC, datetime
from urllib.parse import urljoin
from uuid import UUID

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.core.url_security import normalize_and_validate_url
from app.models.source import Chunk, Document, ProcessingJob, Source
from app.services.source_content import (
    ChunkDraft,
    clean_html,
    clean_plain_text,
    count_words,
    create_semantic_chunks,
    detect_language,
    extract_pdf,
    read_limited_response,
)
from app.services.source_storage import SourceStorage

STAGES = ["fetching", "extracting", "cleaning", "chunking", "saving", "analyzing"]
STAGE_PROGRESS = {
    "fetching": 10,
    "extracting": 30,
    "cleaning": 50,
    "chunking": 70,
    "saving": 90,
    "analyzing": 95,
}


class DuplicateSourceRemoved(Exception):
    pass


class SourceProcessor:
    def __init__(self, db: Session, storage: SourceStorage | None = None) -> None:
        self.db = db
        self.storage = storage or SourceStorage()

    def process(self, source_id: UUID, job_id: UUID) -> None:
        source = self.db.get(Source, source_id)
        job = self.db.get(ProcessingJob, job_id)
        if not source or not job:
            return

        try:
            self._start(source, job)
            first_stage = STAGES.index(job.stage)
            drafts: list[ChunkDraft] | None = None
            for stage in STAGES[first_stage:]:
                self._mark_stage(job, stage)
                if stage == "fetching":
                    self.fetch(source)
                elif stage == "extracting":
                    self.extract(source)
                elif stage == "cleaning":
                    self.clean(source)
                elif stage == "chunking":
                    drafts = self.chunk(source)
                elif stage == "saving":
                    self.save(source, drafts or self.chunk(source))
                elif stage == "analyzing":
                    from app.services.concept_extraction import analyze_source_if_configured

                    analyze_source_if_configured(self.db, source.id, job.id)
            self._complete(source, job)
        except DuplicateSourceRemoved:
            return
        except Exception as error:
            self._fail(source, job, error)

    def fetch(self, source: Source) -> None:
        if source.type == "url":
            if not source.url:
                raise AppError(422, "SOURCE_URL_REQUIRED", "A URL source requires a URL.")
            content = self._fetch_url(source.url)
            self.storage.save(source.id, content)
            return
        if not self.storage.path_for(source.id).exists():
            raise AppError(
                422, "SOURCE_CONTENT_MISSING", "The submitted source content is missing."
            )

    def extract(self, source: Source) -> Document:
        content = self.storage.read(source.id)
        if source.type == "pdf":
            raw_content = extract_pdf(content)
        else:
            raw_content = content.decode("utf-8", errors="replace")
        if not raw_content.strip():
            raise AppError(422, "EMPTY_SOURCE", "No readable content was found in the source.")

        version = self.db.scalar(
            select(func.coalesce(func.max(Document.version), 0)).where(
                Document.source_id == source.id
            )
        )
        document = Document(
            source_id=source.id,
            version=int(version or 0) + 1,
            raw_content=raw_content,
            created_at=datetime.now(UTC),
        )
        self.db.add(document)
        self.db.commit()
        return document

    def clean(self, source: Source) -> Document:
        document = self._latest_document(source.id)
        if source.type == "url":
            document.clean_content, discovered_title = clean_html(document.raw_content)
            if discovered_title and source.title == source.url:
                source.title = discovered_title[:300]
        else:
            document.clean_content = clean_plain_text(document.raw_content)
        if not document.clean_content:
            raise AppError(422, "EMPTY_SOURCE", "No meaningful content remained after cleaning.")
        self.db.commit()
        return document

    def chunk(self, source: Source) -> list[ChunkDraft]:
        document = self._latest_document(source.id)
        drafts = create_semantic_chunks(document.clean_content)
        if not drafts:
            raise AppError(422, "CHUNKING_FAILED", "The source could not be divided into chunks.")
        return drafts

    def save(self, source: Source, drafts: list[ChunkDraft]) -> None:
        document = self._latest_document(source.id)
        content_hash = hashlib.sha256(document.clean_content.encode()).hexdigest()
        duplicate = self.db.scalar(
            select(Source).where(
                Source.workspace_id == source.workspace_id,
                Source.content_hash == content_hash,
                Source.id != source.id,
            )
        )
        if duplicate:
            self.storage.delete(source.id)
            self.db.delete(source)
            self.db.commit()
            raise DuplicateSourceRemoved

        self.db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        for position, draft in enumerate(drafts):
            self.db.add(
                Chunk(
                    document_id=document.id,
                    position=position,
                    heading_path=draft.heading_path,
                    content=draft.content,
                    token_count=draft.token_count,
                    created_at=datetime.now(UTC),
                )
            )
        document.content_hash = content_hash
        document.word_count = count_words(document.clean_content)
        source.content_hash = content_hash
        source.language = detect_language(document.clean_content)
        self.db.commit()

    def _fetch_url(self, url: str) -> bytes:
        current_url = url
        with httpx.Client(
            timeout=settings.source_fetch_timeout_seconds, follow_redirects=False
        ) as client:
            for redirect_count in range(settings.source_max_redirects + 1):
                with client.stream(
                    "GET", current_url, headers={"User-Agent": "PathGraph/1.0"}
                ) as response:
                    if response.is_redirect:
                        if redirect_count >= settings.source_max_redirects:
                            raise AppError(
                                422,
                                "TOO_MANY_REDIRECTS",
                                "The URL redirected too many times.",
                            )
                        location = response.headers.get("location")
                        if not location:
                            raise AppError(
                                422,
                                "INVALID_REDIRECT",
                                "The URL returned an invalid redirect.",
                            )
                        current_url = normalize_and_validate_url(urljoin(current_url, location))
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if content_type not in {"text/html", "text/plain"}:
                        raise AppError(
                            422,
                            "UNSUPPORTED_CONTENT_TYPE",
                            "URL sources must return HTML or plain text.",
                        )
                    return read_limited_response(response)
        raise AppError(422, "SOURCE_FETCH_FAILED", "The URL could not be fetched.")

    def _latest_document(self, source_id: UUID) -> Document:
        document = self.db.scalar(
            select(Document)
            .where(Document.source_id == source_id)
            .order_by(Document.version.desc())
        )
        if not document:
            raise AppError(422, "DOCUMENT_MISSING", "The extracted document is missing.")
        return document

    def _start(self, source: Source, job: ProcessingJob) -> None:
        source.status = "processing"
        job.status = "running"
        job.attempt_count += 1
        job.error_code = None
        job.error_message = None
        job.started_at = datetime.now(UTC)
        job.finished_at = None
        self.db.commit()

    def _mark_stage(self, job: ProcessingJob, stage: str) -> None:
        job.stage = stage
        job.progress = STAGE_PROGRESS[stage]
        self.db.commit()

    def _complete(self, source: Source, job: ProcessingJob) -> None:
        source.status = "ready"
        job.status = "completed"
        job.progress = 100
        job.finished_at = datetime.now(UTC)
        self.db.commit()

    def _fail(self, source: Source, job: ProcessingJob, error: Exception) -> None:
        self.db.rollback()
        source.status = "failed"
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        if isinstance(error, AppError):
            job.error_code = error.code
            job.error_message = error.message
        elif (
            job.stage == "analyzing"
            and isinstance(error, httpx.HTTPStatusError)
            and error.response.status_code == 429
        ):
            job.error_code = "AI_RATE_LIMITED"
            job.error_message = "The AI request limit was reached. Please wait and try again."
        elif job.stage == "analyzing" and isinstance(error, httpx.HTTPError):
            job.error_code = "AI_ANALYSIS_FAILED"
            job.error_message = "The AI provider could not analyze this material. Please retry."
        elif isinstance(error, httpx.HTTPError):
            job.error_code = "SOURCE_FETCH_FAILED"
            job.error_message = "The remote source could not be fetched."
        else:
            job.error_code = "PROCESSING_FAILED"
            job.error_message = "Source processing failed unexpectedly."
        self.db.commit()


def process_source_task(source_id: UUID, job_id: UUID) -> None:
    with SessionLocal() as db:
        SourceProcessor(db).process(source_id, job_id)

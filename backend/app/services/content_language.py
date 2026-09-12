from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import Document, Source
from app.services.source_content import detect_language

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def language_instructions(db: Session, source_ids: list[UUID]) -> str:
    sources = list(db.scalars(select(Source).where(Source.id.in_(source_ids))))
    languages: set[str] = set()
    for source in sources:
        language = source.language
        if language not in {"ru", "en"}:
            document = db.scalar(
                select(Document)
                .where(Document.source_id == source.id)
                .order_by(Document.version.desc())
            )
            language = detect_language(document.clean_content) if document else "und"
        languages.add(language or "und")
    filename = "language_bilingual_v1.txt" if "en" in languages else "language_ru_v1.txt"
    return (PROMPT_DIR / filename).read_text()

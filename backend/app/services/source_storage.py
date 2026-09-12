from pathlib import Path
from uuid import UUID

from app.core.config import settings


class SourceStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.source_storage_dir).resolve()

    def save(self, source_id: UUID, content: bytes) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.path_for(source_id)
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)

    def read(self, source_id: UUID) -> bytes:
        return self.path_for(source_id).read_bytes()

    def delete(self, source_id: UUID) -> None:
        self.path_for(source_id).unlink(missing_ok=True)

    def path_for(self, source_id: UUID) -> Path:
        return self.root / str(source_id)

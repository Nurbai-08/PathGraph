from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.source import Source
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.source_storage import SourceStorage


class WorkspaceService:
    def __init__(
        self, db: Session, user_id: UUID, storage: SourceStorage | None = None
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.storage = storage or SourceStorage()

    def list(self) -> list[Workspace]:
        query = (
            select(Workspace)
            .where(Workspace.user_id == self.user_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(self.db.scalars(query))

    def create(self, payload: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            user_id=self.user_id,
            name=payload.name.strip(),
            description=payload.description.strip(),
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def get(self, workspace_id: UUID) -> Workspace:
        workspace = self.db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.user_id == self.user_id,
            )
        )
        if not workspace:
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found.")
        return workspace

    def update(self, workspace_id: UUID, payload: WorkspaceUpdate) -> Workspace:
        workspace = self.get(workspace_id)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            changes["name"] = changes["name"].strip()
        if "description" in changes:
            changes["description"] = changes["description"].strip()
        for field, value in changes.items():
            setattr(workspace, field, value)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def delete(self, workspace_id: UUID) -> None:
        workspace = self.get(workspace_id)
        source_ids = list(
            self.db.scalars(select(Source.id).where(Source.workspace_id == workspace_id))
        )
        self.db.delete(workspace)
        self.db.commit()
        for source_id in source_ids:
            self.storage.delete(source_id)

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.ai import AISetting
    from app.models.workspace import Workspace


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firebase_uid: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ai_setting: Mapped["AISetting | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

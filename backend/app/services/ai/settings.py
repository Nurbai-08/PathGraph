from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.ai import AISetting
from app.schemas.ai import AISettingsRead, AISettingsUpdate
from app.services.ai.credentials import CredentialCipher


class AISettingsService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    def get(self) -> AISetting | None:
        setting = self.db.scalar(select(AISetting).where(AISetting.user_id == self.user_id))
        if setting or not settings.gemini_api_key:
            return setting

        # Provision the deployment-level Gemini key for a new Firebase user once.
        # It is encrypted before being persisted and is never returned to the client.
        setting = AISetting(
            user_id=self.user_id,
            provider="gemini",
            model=settings.gemini_model,
            embedding_model=settings.gemini_embedding_model,
            api_key_encrypted=CredentialCipher().encrypt(settings.gemini_api_key),
        )
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def require(self) -> AISetting:
        setting = self.get()
        if not setting:
            raise AppError(409, "AI_NOT_CONFIGURED", "Configure an AI provider first.")
        return setting

    def update(self, payload: AISettingsUpdate) -> AISetting:
        setting = self.get()
        if not setting:
            setting = AISetting(user_id=self.user_id)
            self.db.add(setting)

        setting.provider = payload.provider
        setting.base_url = str(payload.base_url).rstrip("/") if payload.base_url else None
        setting.model = payload.model.strip()
        setting.embedding_model = payload.embedding_model.strip()
        if payload.api_key:
            setting.api_key_encrypted = CredentialCipher().encrypt(payload.api_key)
        if payload.provider == "gemini" and not setting.api_key_encrypted:
            raise AppError(422, "GEMINI_API_KEY_REQUIRED", "Gemini requires an API key.")
        if payload.provider == "ollama":
            setting.api_key_encrypted = None
        self.db.commit()
        self.db.refresh(setting)
        return setting


def settings_response(setting: AISetting) -> AISettingsRead:
    return AISettingsRead(
        provider=setting.provider,
        base_url=setting.base_url,
        model=setting.model,
        embedding_model=setting.embedding_model,
        has_api_key=bool(setting.api_key_encrypted),
    )

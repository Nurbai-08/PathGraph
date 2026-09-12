from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import CurrentUser, DbSession
from app.core.errors import AppError
from app.schemas.ai import AIHealthRead, AISettingsRead, AISettingsUpdate
from app.schemas.common import ApiResponse
from app.services.ai.factory import create_provider
from app.services.ai.settings import AISettingsService, settings_response

router = APIRouter(prefix="/ai", tags=["ai settings"])


class ConnectionProbe(BaseModel):
    ok: bool


@router.get("/settings", response_model=ApiResponse[AISettingsRead])
def get_ai_settings(user: CurrentUser, db: DbSession) -> ApiResponse[AISettingsRead]:
    setting = AISettingsService(db, user.id).get()
    if not setting:
        raise AppError(404, "AI_SETTINGS_NOT_FOUND", "AI settings have not been configured.")
    return ApiResponse(data=settings_response(setting))


@router.put("/settings", response_model=ApiResponse[AISettingsRead])
def update_ai_settings(
    payload: AISettingsUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[AISettingsRead]:
    setting = AISettingsService(db, user.id).update(payload)
    return ApiResponse(data=settings_response(setting))


@router.get("/health", response_model=ApiResponse[AIHealthRead])
def check_ai_health(user: CurrentUser, db: DbSession) -> ApiResponse[AIHealthRead]:
    setting = AISettingsService(db, user.id).require()
    provider = create_provider(setting)
    available = provider.health_check()
    if available:
        try:
            probe = provider.generate_structured('Return {"ok": true}.', ConnectionProbe)
            available = probe.ok and bool(provider.embed("Connection test"))
        except Exception:
            available = False
    return ApiResponse(
        data=AIHealthRead(
            available=available,
            provider=provider.provider_name,
            model=provider.model,
        )
    )

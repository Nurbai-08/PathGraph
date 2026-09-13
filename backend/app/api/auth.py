from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token
from app.schemas.auth import AuthCredentials, FirebaseTokenRequest, UserRead
from app.schemas.common import ApiResponse
from app.services.auth import AuthService
from app.services.firebase_auth import verify_firebase_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[UserRead], status_code=status.HTTP_201_CREATED)
def register(payload: AuthCredentials, response: Response, db: DbSession) -> ApiResponse[UserRead]:
    require_local_auth()
    user = AuthService(db).register(payload.email, payload.password)
    set_session_cookie(response, create_access_token(user.id))
    return ApiResponse(data=UserRead.model_validate(user))


@router.post("/login", response_model=ApiResponse[UserRead])
def login(payload: AuthCredentials, response: Response, db: DbSession) -> ApiResponse[UserRead]:
    require_local_auth()
    user = AuthService(db).authenticate(payload.email, payload.password)
    set_session_cookie(response, create_access_token(user.id))
    return ApiResponse(data=UserRead.model_validate(user))


@router.post("/firebase/session", response_model=ApiResponse[UserRead])
def firebase_session(
    payload: FirebaseTokenRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[UserRead]:
    validate_request_origin(request)
    identity = verify_firebase_id_token(payload.id_token)
    user = AuthService(db).authenticate_firebase(identity)
    set_session_cookie(response, create_access_token(user.id))
    return ApiResponse(data=UserRead.model_validate(user))


@router.post("/logout", response_model=ApiResponse[dict[str, bool]])
def logout(response: Response) -> ApiResponse[dict[str, bool]]:
    response.delete_cookie(
        "pathgraph_session",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return ApiResponse(data={"logged_out": True})


@router.get("/me", response_model=ApiResponse[UserRead])
def current_user(user: CurrentUser) -> ApiResponse[UserRead]:
    return ApiResponse(data=UserRead.model_validate(user))


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "pathgraph_session",
        token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def validate_request_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    same_origin = origin == str(request.base_url).rstrip("/") if origin else False
    if origin and origin not in settings.cors_origins and not same_origin:
        raise AppError(403, "INVALID_ORIGIN", "This request origin is not allowed.")


def require_local_auth() -> None:
    if not settings.local_auth_enabled:
        raise AppError(404, "LOCAL_AUTH_DISABLED", "Use Firebase Authentication to sign in.")

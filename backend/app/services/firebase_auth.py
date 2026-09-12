import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from firebase_admin import App, auth, credentials, get_app, initialize_app
from firebase_admin.exceptions import FirebaseError
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token

from app.core.config import settings
from app.core.errors import AppError

APP_NAME = "pathgraph"
MAX_AUTH_AGE_SECONDS = 5 * 60


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str
    email_verified: bool


class FirebaseTokenVerifier:
    def verify(self, id_token: str) -> FirebaseIdentity:
        try:
            claims = self._verify_claims(id_token)
        except (ValueError, FirebaseError) as error:
            raise AppError(
                401,
                "INVALID_FIREBASE_TOKEN",
                "Firebase sign-in has expired.",
            ) from error
        except GoogleAuthError as error:
            raise AppError(
                503,
                "FIREBASE_UNAVAILABLE",
                "Firebase credentials are unavailable on the server.",
            ) from error

        self._validate_issuer(claims.get("iss"))
        self._validate_recent_sign_in(claims.get("auth_time"))
        uid = claims.get("uid") or claims.get("sub")
        email = claims.get("email")
        if not isinstance(uid, str) or not isinstance(email, str):
            raise AppError(401, "INVALID_FIREBASE_TOKEN", "Firebase identity is incomplete.")
        return FirebaseIdentity(
            uid=uid,
            email=email.strip().lower(),
            email_verified=claims.get("email_verified") is True,
        )

    def _verify_claims(self, id_token: str) -> dict[str, object]:
        project_id = self._project_id()
        if self._has_admin_credentials():
            return auth.verify_id_token(id_token, app=self._app(), check_revoked=True)
        return google_id_token.verify_firebase_token(
            id_token,
            GoogleRequest(),
            audience=project_id,
            clock_skew_in_seconds=30,
        )

    def _app(self) -> App:
        project_id = self._project_id()
        try:
            return get_app(APP_NAME)
        except ValueError:
            return initialize_app(
                credential=self._credential(),
                options={"projectId": project_id},
                name=APP_NAME,
            )

    @staticmethod
    def _project_id() -> str:
        if settings.firebase_project_id:
            return settings.firebase_project_id
        raise AppError(
            503,
            "FIREBASE_NOT_CONFIGURED",
            "FIREBASE_PROJECT_ID is not configured on the server.",
        )

    @staticmethod
    def _has_admin_credentials() -> bool:
        return bool(
            settings.firebase_credentials_json or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

    @staticmethod
    def _credential() -> credentials.Base | None:
        if not settings.firebase_credentials_json:
            return None
        try:
            value = json.loads(settings.firebase_credentials_json)
            return credentials.Certificate(value)
        except (TypeError, ValueError) as error:
            raise AppError(
                503,
                "INVALID_FIREBASE_CREDENTIALS",
                "FIREBASE_CREDENTIALS_JSON is invalid.",
            ) from error

    @staticmethod
    def _validate_recent_sign_in(auth_time: object) -> None:
        now = int(datetime.now(UTC).timestamp())
        is_recent = (
            isinstance(auth_time, int)
            and auth_time <= now + 60
            and now - auth_time <= MAX_AUTH_AGE_SECONDS
        )
        if not is_recent:
            raise AppError(401, "RECENT_SIGN_IN_REQUIRED", "Sign in to Firebase again.")

    @staticmethod
    def _validate_issuer(issuer: object) -> None:
        expected = f"https://securetoken.google.com/{settings.firebase_project_id}"
        if issuer != expected:
            raise AppError(401, "INVALID_FIREBASE_TOKEN", "Firebase token issuer is invalid.")


def verify_firebase_id_token(id_token: str) -> FirebaseIdentity:
    return FirebaseTokenVerifier().verify(id_token)

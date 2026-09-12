import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError


class CredentialCipher:
    def __init__(self, secret: str | None = None) -> None:
        raw_secret = secret or settings.credential_encryption_key
        if not raw_secret:
            raise AppError(
                503,
                "ENCRYPTION_NOT_CONFIGURED",
                "Credential encryption must be configured before saving an API key.",
            )
        key = base64.urlsafe_b64encode(hashlib.sha256(raw_secret.encode()).digest())
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken as error:
            raise AppError(
                503,
                "CREDENTIAL_DECRYPTION_FAILED",
                "The saved API key is unreadable.",
            ) from error

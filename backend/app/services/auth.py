from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.firebase_auth import FirebaseIdentity


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        existing_user = self.db.scalar(select(User).where(User.email == normalized_email))
        if existing_user:
            raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email exists.")

        user = User(email=normalized_email, password_hash=hash_password(password))
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise AppError(
                409,
                "EMAIL_ALREADY_REGISTERED",
                "An account with this email exists.",
            ) from error
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        user = self.db.scalar(select(User).where(User.email == normalized_email))
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
        return user

    def authenticate_firebase(self, identity: FirebaseIdentity) -> User:
        user = self.db.scalar(select(User).where(User.firebase_uid == identity.uid))
        if user:
            return user

        user = self.db.scalar(select(User).where(User.email == identity.email))
        if user:
            return self._link_existing_user(user, identity)
        return self._create_firebase_user(identity)

    def _link_existing_user(self, user: User, identity: FirebaseIdentity) -> User:
        if user.firebase_uid and user.firebase_uid != identity.uid:
            raise AppError(409, "FIREBASE_ACCOUNT_CONFLICT", "This email is already linked.")
        if not identity.email_verified:
            raise AppError(
                409,
                "EMAIL_VERIFICATION_REQUIRED",
                "Verify the Firebase email before linking this account.",
            )
        user.firebase_uid = identity.uid
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_firebase_user(self, identity: FirebaseIdentity) -> User:
        user = User(email=identity.email, firebase_uid=identity.uid, password_hash=None)
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise AppError(
                409,
                "FIREBASE_ACCOUNT_CONFLICT",
                "This account is already linked.",
            ) from error
        self.db.refresh(user)
        return user

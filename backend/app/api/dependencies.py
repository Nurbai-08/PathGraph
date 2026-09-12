from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    pathgraph_session: Annotated[str | None, Cookie()] = None,
) -> User:
    if not pathgraph_session:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication is required.")

    user_id = decode_access_token(pathgraph_session)
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise AppError(401, "INVALID_SESSION", "Your session is invalid or expired.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

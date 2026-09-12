from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class FirebaseTokenRequest(BaseModel):
    id_token: str = Field(min_length=20, max_length=8192)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class AISettingsUpdate(BaseModel):
    provider: Literal["ollama", "gemini"]
    base_url: HttpUrl | None = None
    model: str = Field(min_length=1, max_length=120)
    embedding_model: str = Field(min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=8, max_length=500)

    @model_validator(mode="after")
    def validate_provider_fields(self) -> "AISettingsUpdate":
        if self.provider == "ollama" and not self.base_url:
            raise ValueError("Ollama requires a base URL.")
        return self


class AISettingsRead(BaseModel):
    provider: Literal["ollama", "gemini"]
    base_url: str | None
    model: str
    embedding_model: str
    has_api_key: bool


class AIHealthRead(BaseModel):
    available: bool
    provider: str
    model: str

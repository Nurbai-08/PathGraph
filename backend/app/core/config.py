from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PathGraph"
    database_url: str = "postgresql+psycopg://pathgraph:pathgraph@localhost:5432/pathgraph"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cookie_secure: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    source_storage_dir: str = "./source-storage"
    source_max_bytes: int = 10 * 1024 * 1024
    source_fetch_timeout_seconds: float = 10.0
    source_max_redirects: int = 3
    credential_encryption_key: str | None = None
    ai_timeout_seconds: float = 60.0
    firebase_project_id: str | None = None
    firebase_credentials_json: str | None = None
    local_auth_enabled: bool = False
    demo_graph_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

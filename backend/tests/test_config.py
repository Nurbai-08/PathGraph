from app.core.config import Settings


def test_neon_database_url_uses_psycopg_v3() -> None:
    configured = Settings(
        jwt_secret="test-secret",
        database_url="postgresql://user:pass@example.test/pathgraph",
    )

    assert configured.database_url == (
        "postgresql+psycopg://user:pass@example.test/pathgraph"
    )

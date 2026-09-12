from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.ai import AISetting
from app.services.ai.providers import OllamaProvider


def register(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "ai@example.com", "password": "secure-password"},
    )


def test_gemini_key_is_encrypted_and_never_returned(client: TestClient) -> None:
    register(client)
    response = client.put(
        "/ai/settings",
        json={
            "provider": "gemini",
            "model": "gemini-test",
            "embedding_model": "gemini-embedding-test",
            "api_key": "super-secret-api-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["has_api_key"] is True
    assert "api_key" not in response.json()["data"]
    with SessionLocal() as db:
        setting = db.scalar(select(AISetting))
        assert setting is not None
        assert setting.api_key_encrypted != "super-secret-api-key"
        assert "super-secret-api-key" not in (setting.api_key_encrypted or "")


def test_ollama_health_reports_unavailable(client: TestClient, monkeypatch) -> None:
    register(client)
    client.put(
        "/ai/settings",
        json={
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model": "gemma3",
            "embedding_model": "embeddinggemma",
        },
    )
    monkeypatch.setattr(OllamaProvider, "health_check", lambda _self: False)

    response = client.get("/ai/health")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "available": False,
        "provider": "ollama",
        "model": "gemma3",
    }

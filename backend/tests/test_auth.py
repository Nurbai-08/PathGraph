from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.firebase_auth import FirebaseIdentity, FirebaseTokenVerifier

USER = {"email": "learner@example.com", "password": "secure-password"}


def test_registration_creates_session_and_returns_user(client: TestClient) -> None:
    response = client.post("/auth/register", json=USER)

    assert response.status_code == 201
    assert response.json()["data"]["email"] == USER["email"]
    assert response.json()["error"] is None
    assert "pathgraph_session" in response.cookies
    assert client.get("/auth/me").status_code == 200


def test_login_with_existing_user(client: TestClient) -> None:
    client.post("/auth/register", json=USER)
    client.post("/auth/logout")

    response = client.post("/auth/login", json=USER)

    assert response.status_code == 200
    assert response.json()["data"]["email"] == USER["email"]


def test_invalid_login_returns_standard_error(client: TestClient) -> None:
    client.post("/auth/register", json=USER)
    client.post("/auth/logout")

    response = client.post(
        "/auth/login",
        json={"email": USER["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "data": None,
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "Email or password is incorrect.",
        },
    }


def test_firebase_session_creates_local_user(client: TestClient, monkeypatch) -> None:
    identity = FirebaseIdentity("firebase-uid", USER["email"], True)
    monkeypatch.setattr("app.api.auth.verify_firebase_id_token", lambda _: identity)

    response = client.post(
        "/auth/firebase/session",
        json={"id_token": "valid-firebase-token-value"},
        headers={"origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] == USER["email"]
    assert "pathgraph_session" in response.cookies
    assert client.get("/auth/me").status_code == 200


def test_firebase_links_verified_existing_user(client: TestClient, monkeypatch) -> None:
    registered = client.post("/auth/register", json=USER).json()["data"]
    client.post("/auth/logout")
    identity = FirebaseIdentity("firebase-uid", USER["email"], True)
    monkeypatch.setattr("app.api.auth.verify_firebase_id_token", lambda _: identity)

    response = client.post(
        "/auth/firebase/session",
        json={"id_token": "valid-firebase-token-value"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == registered["id"]


def test_firebase_session_rejects_unknown_origin(client: TestClient, monkeypatch) -> None:
    identity = FirebaseIdentity("firebase-uid", USER["email"], True)
    monkeypatch.setattr("app.api.auth.verify_firebase_id_token", lambda _: identity)

    response = client.post(
        "/auth/firebase/session",
        json={"id_token": "valid-firebase-token-value"},
        headers={"origin": "https://attacker.example"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_ORIGIN"


def test_firebase_token_uses_public_verification_without_admin_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(settings, "firebase_credentials_json", None)
    monkeypatch.setattr(settings, "firebase_project_id", "test-firebase-project")
    now = int(datetime.now(UTC).timestamp())
    claims = {
        "sub": "public-firebase-uid",
        "email": USER["email"],
        "email_verified": True,
        "auth_time": now,
        "iss": "https://securetoken.google.com/test-firebase-project",
    }
    monkeypatch.setattr(
        "app.services.firebase_auth.google_id_token.verify_firebase_token",
        lambda *_args, **_kwargs: claims,
    )

    identity = FirebaseTokenVerifier().verify("firebase-id-token")

    assert identity.uid == "public-firebase-uid"
    assert identity.email_verified is True

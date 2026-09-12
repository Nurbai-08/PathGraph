from fastapi.testclient import TestClient


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "secure-password"},
    )
    assert response.status_code == 201


def test_workspace_creation(client: TestClient) -> None:
    register(client, "owner@example.com")

    response = client.post(
        "/workspaces",
        json={"name": "Python Backend", "description": "Learning plan"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Python Backend"
    assert client.get("/workspaces").json()["data"] == [response.json()["data"]]


def test_workspace_permissions_hide_other_users_data(client: TestClient) -> None:
    register(client, "first@example.com")
    workspace = client.post("/workspaces", json={"name": "Private"}).json()["data"]
    client.post("/auth/logout")
    register(client, "second@example.com")

    assert client.get("/workspaces").json()["data"] == []
    assert client.get(f"/workspaces/{workspace['id']}").status_code == 404
    update_response = client.patch(f"/workspaces/{workspace['id']}", json={"name": "Stolen"})
    assert update_response.status_code == 404
    assert client.delete(f"/workspaces/{workspace['id']}").status_code == 404


def test_workspace_deletion(client: TestClient) -> None:
    register(client, "owner@example.com")
    workspace = client.post("/workspaces", json={"name": "Temporary"}).json()["data"]

    response = client.delete(f"/workspaces/{workspace['id']}")

    assert response.status_code == 200
    assert response.json()["data"] == {"deleted": True}
    assert client.get(f"/workspaces/{workspace['id']}").status_code == 404

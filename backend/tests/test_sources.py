from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.errors import AppError
from app.services.source_processing import SourceProcessor


def register_and_create_workspace(client: TestClient, email: str = "source@example.com") -> str:
    client.post("/auth/register", json={"email": email, "password": "secure-password"})
    response = client.post("/workspaces", json={"name": "Backend"})
    return response.json()["data"]["id"]


def add_text_source(
    client: TestClient,
    workspace_id: str,
    text: str = "# HTTP\n\nRequests and responses.",
):
    return client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "text", "title": "HTTP", "text": text},
    )


def test_text_source_creates_document_and_chunks(client: TestClient) -> None:
    workspace_id = register_and_create_workspace(client)

    response = add_text_source(client, workspace_id)
    source_id = response.json()["data"]["id"]
    detail = client.get(f"/sources/{source_id}").json()["data"]

    assert response.status_code == 201
    assert detail["status"] == "ready"
    assert detail["document"]["word_count"] == 4
    assert detail["document"]["chunks"][0]["heading_path"] == "HTTP"
    assert detail["job"]["status"] == "completed"


def test_duplicate_text_is_rejected(client: TestClient) -> None:
    workspace_id = register_and_create_workspace(client)
    assert add_text_source(client, workspace_id).status_code == 201

    response = add_text_source(client, workspace_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_SOURCE"
    assert len(client.get("/sources", params={"workspace_id": workspace_id}).json()["data"]) == 1


def test_url_source_is_normalized_and_duplicate_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = register_and_create_workspace(client)
    monkeypatch.setattr(
        "app.core.url_security.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    monkeypatch.setattr(
        SourceProcessor,
        "_fetch_url",
        lambda _self, _url: b"<html><body><h1>HTTP</h1><p>Public content</p></body></html>",
    )

    first = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "url", "url": "HTTP://Example.com:80/a#b"},
    )
    duplicate = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "url", "url": "http://example.com/a"},
    )

    assert first.status_code == 201
    assert first.json()["data"]["url"] == "http://example.com/a"
    assert duplicate.status_code == 409


def test_different_urls_with_same_content_collapse_to_one_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = register_and_create_workspace(client)
    monkeypatch.setattr(
        "app.core.url_security.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    monkeypatch.setattr(
        SourceProcessor,
        "_fetch_url",
        lambda _self, _url: b"<html><body><p>Identical content</p></body></html>",
    )

    client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "url", "url": "https://one.example/a"},
    )
    client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "url", "url": "https://two.example/b"},
    )

    sources = client.get("/sources", params={"workspace_id": workspace_id}).json()["data"]
    assert len(sources) == 1


def test_pdf_source_is_extracted(client: TestClient) -> None:
    workspace_id = register_and_create_workspace(client)
    pdf = make_text_pdf("Hello PDF")

    response = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "pdf", "title": "Guide"},
        files={"file": ("guide.pdf", pdf, "application/pdf")},
    )
    source_id = response.json()["data"]["id"]
    detail = client.get(f"/sources/{source_id}").json()["data"]

    assert response.status_code == 201
    assert detail["status"] == "ready"
    assert "Hello PDF" in detail["document"]["clean_content"]


def test_failed_chunking_retries_from_same_document(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = register_and_create_workspace(client)
    original_chunk: Callable = SourceProcessor.chunk
    attempts = 0

    def fail_once(processor: SourceProcessor, source):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise AppError(422, "CHUNKING_FAILED", "Temporary chunking failure.")
        return original_chunk(processor, source)

    monkeypatch.setattr(SourceProcessor, "chunk", fail_once)
    response = add_text_source(client, workspace_id)
    source_id = response.json()["data"]["id"]
    failed = client.get(f"/sources/{source_id}").json()["data"]

    assert failed["status"] == "failed"
    assert failed["job"]["stage"] == "chunking"
    retry = client.post(f"/sources/{source_id}/retry")
    completed = client.get(f"/sources/{source_id}").json()["data"]
    assert retry.status_code == 200
    assert completed["status"] == "ready"
    assert completed["job"]["attempt_count"] == 2
    assert completed["document"]["version"] == 1


def test_processing_failure_and_source_deletion(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = register_and_create_workspace(client)
    monkeypatch.setattr(
        SourceProcessor,
        "clean",
        lambda _self, _source: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    response = add_text_source(client, workspace_id)
    source_id = response.json()["data"]["id"]
    failed = client.get(f"/sources/{source_id}").json()["data"]

    assert failed["status"] == "failed"
    assert failed["job"]["error_code"] == "PROCESSING_FAILED"
    assert client.delete(f"/sources/{source_id}").status_code == 200
    assert client.get(f"/sources/{source_id}").status_code == 404


def test_ai_rate_limit_is_not_reported_as_url_fetch_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = register_and_create_workspace(client)
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    response = httpx.Response(429, request=request)

    def rate_limited(*_args):
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(
        "app.services.concept_extraction.analyze_source_if_configured",
        rate_limited,
    )
    created = add_text_source(client, workspace_id)
    detail = client.get(f"/sources/{created.json()['data']['id']}").json()["data"]

    assert detail["status"] == "failed"
    assert detail["job"]["stage"] == "analyzing"
    assert detail["job"]["error_code"] == "AI_RATE_LIMITED"
    assert "request limit" in detail["job"]["error_message"]


def test_demo_mode_builds_graph_without_ai_credentials(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "demo_graph_enabled", True)
    workspace_id = register_and_create_workspace(client)

    response = add_text_source(
        client,
        workspace_id,
        "# Neural Networks\n\nNeurons learn representations.\n\n"
        "## Backpropagation\n\nGradients update network weights.",
    )
    graph = client.get(f"/workspaces/{workspace_id}/graph", params={"overview": True})

    assert response.status_code == 201
    assert graph.status_code == 200
    assert len(graph.json()["data"]["nodes"]) >= 2
    assert len(graph.json()["data"]["edges"]) >= 1


def make_text_pdf(text: str) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        (
            f"<< /Length {len(text) + 30} >>\nstream\n"
            f"BT /F1 18 Tf 20 80 Td ({text}) Tj ET\nendstream"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode() + item + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(result)

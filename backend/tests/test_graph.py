from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.concept import Concept, ConceptAlias, ConceptEdge, ConceptSource
from app.models.source import Chunk, Document


def setup_workspace(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "graph@example.com", "password": "secure-password"},
    )
    return client.post("/workspaces", json={"name": "Graph"}).json()["data"]["id"]


def add_source(client: TestClient, workspace_id: str, text: str) -> str:
    response = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "text", "text": text},
    )
    return response.json()["data"]["id"]


def test_graph_concept_panel_neighbors_and_search(client: TestClient) -> None:
    workspace_id = setup_workspace(client)
    source_id = add_source(client, workspace_id, "Python enables FastAPI.")
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.source_id == UUID(source_id)))
        python = Concept(
            workspace_id=UUID(workspace_id),
            name="Python",
            normalized_name="python",
            description="A programming language",
            type="language",
            importance=0.9,
            confidence=0.95,
        )
        fastapi = Concept(
            workspace_id=UUID(workspace_id),
            name="FastAPI",
            normalized_name="fastapi",
            description="A Python API framework",
            type="framework",
            importance=0.8,
            confidence=0.9,
        )
        db.add_all([python, fastapi])
        db.flush()
        db.add_all(
            [
                ConceptAlias(concept_id=python.id, alias="Py", normalized_alias="py"),
                ConceptSource(
                    concept_id=fastapi.id,
                    source_id=UUID(source_id),
                    chunk_id=document.chunks[0].id,
                    confidence=0.9,
                ),
                ConceptEdge(
                    workspace_id=UUID(workspace_id),
                    source_concept_id=python.id,
                    target_concept_id=fastapi.id,
                    relation_type="prerequisite_of",
                    confidence=0.9,
                ),
            ]
        )
        db.commit()
        python_id = str(python.id)
        fastapi_id = str(fastapi.id)

    graph = client.get(f"/workspaces/{workspace_id}/graph", params={"overview": True})
    detail = client.get(f"/concepts/{fastapi_id}")
    neighbors = client.get(f"/concepts/{python_id}/neighbors")
    search = client.get(f"/workspaces/{workspace_id}/concepts/search", params={"q": "py"})

    assert graph.status_code == 200
    assert len(graph.json()["data"]["nodes"]) == 2
    assert detail.json()["data"]["prerequisites"][0]["name"] == "Python"
    assert detail.json()["data"]["sources"][0]["title"] == "Text source"
    assert len(neighbors.json()["data"]["nodes"]) == 2
    assert search.json()["data"][0]["name"] == "Python"


def test_overview_limits_large_graph(client: TestClient) -> None:
    workspace_id = setup_workspace(client)
    with SessionLocal() as db:
        db.add_all(
            [
                Concept(
                    workspace_id=UUID(workspace_id),
                    name=f"Concept {index}",
                    normalized_name=f"concept {index}",
                    importance=index / 250,
                    confidence=0.8,
                )
                for index in range(205)
            ]
        )
        db.commit()

    response = client.get(f"/workspaces/{workspace_id}/graph", params={"overview": True})

    assert len(response.json()["data"]["nodes"]) == 50
    assert response.json()["data"]["truncated"] is True


def test_graph_can_be_filtered_by_source(client: TestClient) -> None:
    workspace_id = setup_workspace(client)
    first_source = add_source(client, workspace_id, "First material.")
    second_source = add_source(client, workspace_id, "Second material.")
    with SessionLocal() as db:
        documents = {
            source_id: db.scalar(select(Document).where(Document.source_id == UUID(source_id)))
            for source_id in [first_source, second_source]
        }
        concepts = [
            Concept(
                workspace_id=UUID(workspace_id),
                name=name,
                normalized_name=name.lower(),
                importance=0.8,
                confidence=0.9,
            )
            for name in ["First", "Second"]
        ]
        db.add_all(concepts)
        db.flush()
        db.add_all(
            [
                ConceptSource(
                    concept_id=concept.id,
                    source_id=UUID(source_id),
                    chunk_id=documents[source_id].chunks[0].id,
                    confidence=0.9,
                )
                for concept, source_id in zip(concepts, [first_source, second_source], strict=True)
            ]
        )
        db.commit()

    response = client.get(
        f"/workspaces/{workspace_id}/graph",
        params={"overview": True, "source_id": second_source},
    )

    assert [node["name"] for node in response.json()["data"]["nodes"]] == ["Second"]


def test_source_deletion_preserves_shared_concept_until_last_evidence(
    client: TestClient,
) -> None:
    workspace_id = setup_workspace(client)
    first_source = add_source(client, workspace_id, "First evidence.")
    second_source = add_source(client, workspace_id, "Second evidence.")
    with SessionLocal() as db:
        chunks = {
            str(source_id): db.scalar(
                select(Chunk).join(Document).where(Document.source_id == UUID(source_id))
            )
            for source_id in [first_source, second_source]
        }
        shared = Concept(
            workspace_id=UUID(workspace_id),
            name="Shared",
            normalized_name="shared",
            importance=0.7,
            confidence=0.8,
        )
        db.add(shared)
        db.flush()
        db.add_all(
            [
                ConceptSource(
                    concept_id=shared.id,
                    source_id=UUID(source_id),
                    chunk_id=chunks[source_id].id,
                    confidence=0.8,
                )
                for source_id in [first_source, second_source]
            ]
        )
        db.commit()

    client.delete(f"/sources/{first_source}")
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Concept.id))) == 1

    client.delete(f"/sources/{second_source}")
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Concept.id))) == 0

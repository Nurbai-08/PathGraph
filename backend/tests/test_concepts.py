import json
from collections import deque
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models.ai import AIRun
from app.models.concept import Concept, ConceptAlias, ConceptEdge, ConceptSource
from app.models.source import Source
from app.schemas.concept import ConceptExtractionOutput
from app.services.ai.providers import AIProvider, AIProviderError
from app.services.concept_extraction import ConceptExtractionService
from app.services.concept_graph import ConceptGraphService


class ScriptedProvider(AIProvider):
    provider_name = "test"
    model = "test-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = deque(responses)
        self.structured_calls = 0

    def generate(self, prompt: str) -> str:
        return self._generate_structured_response(prompt, {})

    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        self.structured_calls += 1
        return self.responses.popleft()

    def embed(self, text: str) -> list[float]:
        normalized = text.lower()
        if "python" in normalized:
            return [0.0, 1.0, 0.0]
        if "fastapi" in normalized:
            return [0.0, 0.0, 1.0]
        return [1.0, 0.0, 0.0]

    def health_check(self) -> bool:
        return True


def source_with_text(client: TestClient, text: str, email: str = "concept@example.com") -> str:
    if client.get("/auth/me").status_code != 200:
        client.post("/auth/register", json={"email": email, "password": "secure-password"})
    workspaces = client.get("/workspaces").json()["data"]
    workspace_id = (
        workspaces[0]["id"]
        if workspaces
        else client.post("/workspaces", json={"name": "Concepts"}).json()["data"]["id"]
    )
    response = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "text", "text": text},
    )
    return response.json()["data"]["id"]


def extraction_payload(concepts: list[dict], relationships: list[dict] | None = None) -> str:
    return json.dumps({"concepts": concepts, "relationships": relationships or []})


def concept(name: str, aliases: list[str] | None = None) -> dict:
    return {
        "name": name,
        "description": f"Description of {name}",
        "type": "technology",
        "importance": 0.8,
        "confidence": 0.9,
        "aliases": aliases or [],
    }


def test_structured_output_repairs_once() -> None:
    provider = ScriptedProvider(["not json", extraction_payload([concept("Python")])])

    result = provider.generate_structured("extract", ConceptExtractionOutput)

    assert result.concepts[0].name == "Python"
    assert provider.structured_calls == 2


def test_invalid_structured_output_fails_after_repair() -> None:
    provider = ScriptedProvider(["bad", "still bad"])

    with pytest.raises(AIProviderError):
        provider.generate_structured("extract", ConceptExtractionOutput)


def test_extraction_merges_aliases_and_keeps_provenance(client: TestClient) -> None:
    first_source = source_with_text(client, "# JavaScript\n\nBrowser language.")
    second_source = source_with_text(client, "# JS\n\nLanguage for web applications.")
    provider = ScriptedProvider(
        [
            extraction_payload([concept("JavaScript", ["JS"])]),
            extraction_payload([concept("JS")]),
        ]
    )

    with SessionLocal() as db:
        ConceptExtractionService(db, provider).run(db.get(Source, UUID(first_source)).id)
        ConceptExtractionService(db, provider).run(db.get(Source, UUID(second_source)).id)
        assert db.scalar(select(func.count(Concept.id))) == 1
        assert db.scalar(select(func.count(ConceptAlias.id))) == 1
        assert db.scalar(select(func.count(ConceptSource.id))) == 2


def test_relationships_are_created_and_cycles_are_rejected(client: TestClient) -> None:
    source_id = source_with_text(client, "# Python and FastAPI\n\nPython is needed for FastAPI.")
    output = extraction_payload(
        [concept("Python"), concept("FastAPI")],
        [
            {
                "source_name": "Python",
                "target_name": "FastAPI",
                "relation_type": "prerequisite_of",
                "confidence": 0.95,
            }
        ],
    )

    with SessionLocal() as db:
        source = db.get(Source, UUID(source_id))
        ConceptExtractionService(db, ScriptedProvider([output])).run(source.id)
        concepts = list(db.scalars(select(Concept).order_by(Concept.name)))
        assert db.scalar(select(func.count(ConceptEdge.id))) == 1
        graph = ConceptGraphService(db, source.workspace_id)
        with pytest.raises(AppError) as error:
            graph.add_edge(concepts[0].id, concepts[1].id, "prerequisite_of", 0.8)
        assert error.value.code == "PREREQUISITE_CYCLE"


def test_bad_chunk_does_not_stop_other_chunks(client: TestClient) -> None:
    source_id = source_with_text(client, "# Bad\n\nFirst chunk.\n\n# Good\n\nSecond chunk.")
    provider = ScriptedProvider(["bad", "still bad", extraction_payload([concept("Good Concept")])])

    with SessionLocal() as db:
        created = ConceptExtractionService(db, provider).run(db.get(Source, UUID(source_id)).id)
        assert created == 1
        assert db.scalar(select(func.count(Concept.id))) == 1
        runs = list(db.scalars(select(AIRun).order_by(AIRun.created_at)))
        assert [run.status for run in runs] == ["failed", "completed"]


def test_invalid_relationship_type_is_rejected(client: TestClient) -> None:
    source_id = source_with_text(client, "One source")
    with SessionLocal() as db:
        source = db.get(Source, UUID(source_id))
        first = Concept(
            workspace_id=source.workspace_id,
            name="A",
            normalized_name="a",
            importance=0.5,
            confidence=0.5,
        )
        second = Concept(
            workspace_id=source.workspace_id,
            name="B",
            normalized_name="b",
            importance=0.5,
            confidence=0.5,
        )
        db.add_all([first, second])
        db.flush()
        with pytest.raises(AppError) as error:
            ConceptGraphService(db, source.workspace_id).add_edge(
                first.id, second.id, "invented_relation", 0.5
            )
        assert error.value.code == "INVALID_RELATION_TYPE"

from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.concept import Concept, ConceptEdge, ConceptSource
from app.models.learning import KnowledgeState
from app.models.source import Document
from app.schemas.interactions import CompareGeneration, GroundedGeneration, WhyGeneration
from app.services.ai.providers import AIProvider
from app.services.interactions import InteractionService


class InteractionProvider(AIProvider):
    provider_name = "test"
    model = "interaction-model"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        return ""

    def generate_structured(self, prompt: str, schema: type[BaseModel]):
        self.prompts.append(prompt)
        if schema is WhyGeneration:
            return WhyGeneration(
                source_backed_answer="HTTP supports web APIs. [1]",
                additional_explanation="It is a useful foundation.",
                citation_indices=[1, 99],
                why_it_matters="It unlocks API design.",
            )
        if schema is CompareGeneration:
            return CompareGeneration(
                similarities=["Both are web concepts."],
                differences=["One is a protocol; one is an interface."],
                when_to_use_a=["Transport messages"],
                when_to_use_b=["Design an application boundary"],
                examples=["GET /users"],
                citation_indices=[1],
            )
        return GroundedGeneration(
            source_backed_answer="HTTP uses request and response messages. [1]",
            additional_explanation="Think of it as a conversation.",
            citation_indices=[1, 99],
        )

    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        return ""

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def health_check(self) -> bool:
        return True


def setup_interaction_data(client: TestClient):
    user = client.post(
        "/auth/register",
        json={"email": "rag@example.com", "password": "secure-password"},
    ).json()["data"]
    workspace_id = client.post("/workspaces", json={"name": "RAG"}).json()["data"]["id"]
    content = "# HTTP\n\nRequests and responses.\n" + "\n".join(
        f"# Irrelevant {index}\n\nUnrelated detail number {index}." for index in range(8)
    )
    source_id = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "text", "text": content},
    ).json()["data"]["id"]
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.source_id == UUID(source_id)))
        chunks = sorted(document.chunks, key=lambda item: item.position)
        chunks[0].embedding = [1.0, 0.0]
        for chunk in chunks[1:]:
            chunk.embedding = [0.0, 1.0]
        http = Concept(
            workspace_id=UUID(workspace_id),
            name="HTTP",
            normalized_name="http",
            description="Web transfer protocol",
            type="protocol",
            importance=0.9,
            confidence=0.9,
        )
        api = Concept(
            workspace_id=UUID(workspace_id),
            name="Web API",
            normalized_name="web api",
            description="Application interface over the web",
            type="architecture",
            importance=0.8,
            confidence=0.9,
        )
        db.add_all([http, api])
        db.flush()
        db.add_all(
            [
                ConceptSource(
                    concept_id=http.id,
                    source_id=UUID(source_id),
                    chunk_id=chunks[0].id,
                    confidence=0.9,
                ),
                ConceptSource(
                    concept_id=api.id,
                    source_id=UUID(source_id),
                    chunk_id=chunks[1].id,
                    confidence=0.8,
                ),
                ConceptEdge(
                    workspace_id=UUID(workspace_id),
                    source_concept_id=http.id,
                    target_concept_id=api.id,
                    relation_type="prerequisite_of",
                    confidence=0.9,
                ),
                KnowledgeState(
                    user_id=UUID(user["id"]),
                    concept_id=http.id,
                    status="learning",
                    mastery=30,
                    confidence=0.6,
                ),
            ]
        )
        db.commit()
        return UUID(user["id"]), UUID(workspace_id), http.id, api.id


def test_explain_uses_bounded_context_and_validated_citations(client: TestClient) -> None:
    user_id, _, http_id, _ = setup_interaction_data(client)
    provider = InteractionProvider()
    with SessionLocal() as db:
        answer = InteractionService(db, user_id, provider).explain(http_id, "simpler")

    assert answer.source_backed_answer.startswith("HTTP uses")
    assert [citation.index for citation in answer.citations] == [1]
    assert answer.citations[0].excerpt == "Requests and responses."
    assert "Learner mastery: 30%" in provider.prompts[0]
    assert "Mode: simpler" in provider.prompts[0]
    assert "Irrelevant 7" not in provider.prompts[0]


def test_why_compare_and_graph_chat(client: TestClient) -> None:
    user_id, workspace_id, http_id, api_id = setup_interaction_data(client)
    provider = InteractionProvider()
    with SessionLocal() as db:
        service = InteractionService(db, user_id, provider)
        why = service.why(http_id)
        comparison = service.compare(workspace_id, http_id, api_id)
        chat = service.chat(workspace_id, "Why does HTTP matter for an API?")

    assert why.path == ["HTTP", "Web API"]
    assert why.why_it_matters == "It unlocks API design."
    assert comparison.concept_a == "HTTP"
    assert comparison.similarities == ["Both are web concepts."]
    assert chat.citations[0].source_title == "Text source"
    assert any("HTTP prerequisite_of Web API" in prompt for prompt in provider.prompts)

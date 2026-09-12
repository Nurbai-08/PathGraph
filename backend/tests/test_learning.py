from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.concept import Concept, ConceptEdge, ConceptSource
from app.models.learning import QuizAttempt, QuizQuestion
from app.models.source import Chunk, Document
from app.schemas.learning import QuizGenerationOutput
from app.services.ai.providers import AIProvider
from app.services.quizzes import QuizService


def setup_learning_graph(client: TestClient) -> tuple[str, dict[str, str], str]:
    user = client.post(
        "/auth/register",
        json={"email": "learner@example.com", "password": "secure-password"},
    ).json()["data"]
    workspace_id = client.post("/workspaces", json={"name": "Learning"}).json()["data"]["id"]
    with SessionLocal() as db:
        concepts = {
            name: Concept(
                workspace_id=UUID(workspace_id),
                name=name,
                normalized_name=name.lower(),
                description=f"Learn {name}",
                type="topic",
                importance=importance,
                confidence=0.9,
            )
            for name, importance in [("HTTP", 0.9), ("Python", 0.8), ("FastAPI", 1.0)]
        }
        db.add_all(concepts.values())
        db.flush()
        db.add_all(
            [
                ConceptEdge(
                    workspace_id=UUID(workspace_id),
                    source_concept_id=concepts[prerequisite].id,
                    target_concept_id=concepts["FastAPI"].id,
                    relation_type="prerequisite_of",
                    confidence=0.9,
                )
                for prerequisite in ["HTTP", "Python"]
            ]
        )
        db.commit()
        ids = {name: str(concept.id) for name, concept in concepts.items()}
    return workspace_id, ids, user["id"]


def test_learning_path_recommends_available_prerequisites(client: TestClient) -> None:
    workspace_id, concepts, _ = setup_learning_graph(client)

    created = client.post(
        f"/workspaces/{workspace_id}/learning-paths",
        json={"goal": "I want to learn FastAPI"},
    )
    path_id = created.json()["data"]["id"]
    first = client.get(f"/learning-paths/{path_id}/next").json()["data"]

    assert created.status_code == 201
    assert [item["concept"]["name"] for item in created.json()["data"]["items"]][-1] == "FastAPI"
    assert first["concept"]["name"] == "HTTP"
    assert {gap["concept"]["name"] for gap in first["gaps"]} == {"HTTP", "Python"}

    client.patch(f"/concepts/{concepts['HTTP']}/knowledge", json={"status": "mastered"})
    second = client.get(f"/learning-paths/{path_id}/next").json()["data"]
    assert second["concept"]["name"] == "Python"

    client.patch(f"/concepts/{concepts['Python']}/knowledge", json={"status": "mastered"})
    third = client.get(f"/learning-paths/{path_id}/next").json()["data"]
    assert third["concept"]["name"] == "FastAPI"


def test_quiz_updates_mastery_gradually(client: TestClient) -> None:
    _, concepts, user_id = setup_learning_graph(client)
    with SessionLocal() as db:
        question = QuizQuestion(
            concept_id=UUID(concepts["HTTP"]),
            question="What does HTTP transfer?",
            type="multiple_choice",
            choices=["Hypertext", "Databases"],
            answer="Hypertext",
            explanation="HTTP transfers hypertext messages.",
            difficulty=1,
            source_chunk_ids=[],
            created_at=datetime.now(UTC),
        )
        db.add(question)
        db.commit()
        question_id = str(question.id)

    first = client.post(
        f"/quiz-questions/{question_id}/answer", json={"answer": "Hypertext"}
    ).json()["data"]
    second = client.post(
        f"/quiz-questions/{question_id}/answer", json={"answer": "Hypertext"}
    ).json()["data"]

    assert first["correct"] is True
    assert first["mastery_after"] == 20
    assert second["mastery_after"] == 36
    assert second["mastery_after"] < 100
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == UUID(user_id))
            )
            == 2
        )


def test_graph_reflects_mastery_and_knowledge_gap(client: TestClient) -> None:
    workspace_id, concepts, _ = setup_learning_graph(client)
    client.patch(f"/concepts/{concepts['FastAPI']}/knowledge", json={"status": "learning"})

    graph = client.get(f"/workspaces/{workspace_id}/graph", params={"overview": True}).json()[
        "data"
    ]
    by_name = {node["name"]: node for node in graph["nodes"]}

    assert by_name["FastAPI"]["mastery"] == 30
    assert by_name["HTTP"]["knowledge_gap"] is True
    assert by_name["Python"]["knowledge_gap"] is True


class QuizProvider(AIProvider):
    provider_name = "test"
    model = "quiz-model"

    def __init__(self, chunk_id: UUID) -> None:
        self.chunk_id = chunk_id

    def generate(self, prompt: str) -> str:
        return ""

    def generate_structured(self, prompt: str, schema):
        return QuizGenerationOutput.model_validate(
            {
                "questions": [
                    {
                        "question": "Which protocol is described?",
                        "type": "multiple_choice",
                        "choices": ["HTTP", "FTP"],
                        "answer": "HTTP",
                        "explanation": "The source describes HTTP.",
                        "difficulty": 1,
                        "source_chunk_ids": [str(self.chunk_id)],
                    }
                ]
            }
        )

    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        return ""

    def embed(self, text: str) -> list[float]:
        return [1.0]

    def health_check(self) -> bool:
        return True


def test_generated_quiz_keeps_chunk_provenance_and_hides_answer(client: TestClient) -> None:
    workspace_id, concepts, user_id = setup_learning_graph(client)
    source_id = client.post(
        "/sources",
        data={"workspace_id": workspace_id, "type": "text", "text": "HTTP is a protocol."},
    ).json()["data"]["id"]
    with SessionLocal() as db:
        chunk = db.scalar(select(Chunk).join(Document).where(Document.source_id == UUID(source_id)))
        db.add(
            ConceptSource(
                concept_id=UUID(concepts["HTTP"]),
                source_id=UUID(source_id),
                chunk_id=chunk.id,
                confidence=0.9,
            )
        )
        db.commit()
        questions = QuizService(db, UUID(user_id)).generate(
            UUID(concepts["HTTP"]), QuizProvider(chunk.id)
        )

    assert questions[0].source_chunk_ids == [chunk.id]
    assert not hasattr(questions[0], "answer")

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.graph import ConceptDetail, GraphNode, GraphRead
from app.services.graph_query import GraphQueryService

router = APIRouter(tags=["knowledge graph"])


@router.get("/workspaces/{workspace_id}/graph", response_model=ApiResponse[GraphRead])
def get_graph(
    workspace_id: UUID,
    user: CurrentUser,
    db: DbSession,
    focus_id: UUID | None = None,
    depth: int = Query(default=2, ge=1, le=3),
    overview: bool = False,
    source_id: UUID | None = None,
) -> ApiResponse[GraphRead]:
    graph = GraphQueryService(db, user.id).graph(workspace_id, focus_id, depth, overview, source_id)
    return ApiResponse(data=graph)


@router.get("/concepts/{concept_id}", response_model=ApiResponse[ConceptDetail])
def get_concept(concept_id: UUID, user: CurrentUser, db: DbSession) -> ApiResponse[ConceptDetail]:
    return ApiResponse(data=GraphQueryService(db, user.id).concept_detail(concept_id))


@router.get("/concepts/{concept_id}/neighbors", response_model=ApiResponse[GraphRead])
def get_neighbors(
    concept_id: UUID,
    user: CurrentUser,
    db: DbSession,
    depth: int = Query(default=2, ge=1, le=3),
) -> ApiResponse[GraphRead]:
    detail = GraphQueryService(db, user.id).concept_detail(concept_id)
    return ApiResponse(
        data=GraphQueryService(db, user.id).graph(
            next_workspace_id(db, detail.id), detail.id, depth
        )
    )


@router.get(
    "/workspaces/{workspace_id}/concepts/search",
    response_model=ApiResponse[list[GraphNode]],
)
def search_concepts(
    workspace_id: UUID,
    q: str,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[list[GraphNode]]:
    return ApiResponse(data=GraphQueryService(db, user.id).search(workspace_id, q))


def next_workspace_id(db: DbSession, concept_id: UUID) -> UUID:
    from app.models.concept import Concept

    concept = db.get(Concept, concept_id)
    return concept.workspace_id

import { apiRequest } from "../../shared/api/client";
import type { ConceptDetail, GraphNode, KnowledgeGraph } from "../../shared/types/graph";

export const conceptApi = {
  graph: (workspaceId: string, focusId?: string, sourceId?: string) => {
    const query = focusId
      ? `focus_id=${encodeURIComponent(focusId)}&depth=2`
      : "overview=true";
    const sourceQuery = sourceId ? `&source_id=${encodeURIComponent(sourceId)}` : "";
    return apiRequest<KnowledgeGraph>(`/workspaces/${workspaceId}/graph?${query}${sourceQuery}`);
  },
  detail: (conceptId: string) => apiRequest<ConceptDetail>(`/concepts/${conceptId}`),
  search: (workspaceId: string, query: string) =>
    apiRequest<GraphNode[]>(
      `/workspaces/${workspaceId}/concepts/search?q=${encodeURIComponent(query)}`,
    ),
};

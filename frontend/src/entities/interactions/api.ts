import { apiRequest } from "../../shared/api/client";
import type { CompareAnswer, GroundedAnswer, WhyAnswer } from "../../shared/types/interactions";

export const interactionsApi = {
  explain: (conceptId: string, mode: "standard" | "simpler") =>
    apiRequest<GroundedAnswer>(`/concepts/${conceptId}/explain`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  why: (conceptId: string) =>
    apiRequest<WhyAnswer>(`/concepts/${conceptId}/why`, { method: "POST" }),
  compare: (workspaceId: string, conceptAId: string, conceptBId: string) =>
    apiRequest<CompareAnswer>(`/workspaces/${workspaceId}/compare`, {
      method: "POST",
      body: JSON.stringify({ concept_a_id: conceptAId, concept_b_id: conceptBId }),
    }),
  chat: (workspaceId: string, question: string) =>
    apiRequest<GroundedAnswer>(`/workspaces/${workspaceId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};


import { apiRequest } from "../../shared/api/client";
import type { LearningPath, NextConcept, QuizQuestion, QuizResult } from "../../shared/types/learning";

export const learningApi = {
  setStatus: (conceptId: string, status: "unseen" | "learning" | "understood" | "mastered") =>
    apiRequest<{ status: string; mastery: number }>(`/concepts/${conceptId}/knowledge`, {
      method: "PATCH", body: JSON.stringify({ status }),
    }),
  listPaths: (workspaceId: string) =>
    apiRequest<LearningPath[]>(`/workspaces/${workspaceId}/learning-paths`),
  createPath: (workspaceId: string, goal: string) =>
    apiRequest<LearningPath>(`/workspaces/${workspaceId}/learning-paths`, {
      method: "POST",
      body: JSON.stringify({ goal }),
    }),
  next: (pathId: string) => apiRequest<NextConcept>(`/learning-paths/${pathId}/next`),
  listQuiz: (conceptId: string) => apiRequest<QuizQuestion[]>(`/concepts/${conceptId}/quiz`),
  generateQuiz: (conceptId: string) =>
    apiRequest<QuizQuestion[]>(`/concepts/${conceptId}/quiz`, { method: "POST" }),
  answer: (questionId: string, answer: string) =>
    apiRequest<QuizResult>(`/quiz-questions/${questionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),
};

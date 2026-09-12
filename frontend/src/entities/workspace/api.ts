import { apiRequest } from "../../shared/api/client";
import type { Workspace, WorkspaceInput } from "../../shared/types/workspace";

export const workspaceApi = {
  list: () => apiRequest<Workspace[]>("/workspaces"),
  get: (workspaceId: string) => apiRequest<Workspace>(`/workspaces/${workspaceId}`),
  create: (input: WorkspaceInput) =>
    apiRequest<Workspace>("/workspaces", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  update: (workspaceId: string, input: Partial<WorkspaceInput>) =>
    apiRequest<Workspace>(`/workspaces/${workspaceId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  delete: (workspaceId: string) =>
    apiRequest<{ deleted: boolean }>(`/workspaces/${workspaceId}`, { method: "DELETE" }),
};


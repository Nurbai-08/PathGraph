import { apiRequest } from "../../shared/api/client";
import type { ProcessingJob, Source, SourceInput } from "../../shared/types/source";

export const sourceApi = {
  detail: (sourceId: string) => apiRequest<Source & { document: { clean_content: string } | null }>(`/sources/${sourceId}`),
  analyze: (sourceId: string) => apiRequest<{ queued: boolean }>(`/sources/${sourceId}/analyze`, { method: "POST" }),
  list: (workspaceId: string) =>
    apiRequest<Source[]>(`/sources?workspace_id=${encodeURIComponent(workspaceId)}`),
  create: (input: SourceInput) => {
    const body = new FormData();
    body.set("workspace_id", input.workspaceId);
    body.set("type", input.type);
    body.set("title", input.title);
    if (input.url) body.set("url", input.url);
    if (input.text) body.set("text", input.text);
    if (input.file) body.set("file", input.file);
    return apiRequest<Source>("/sources", { method: "POST", body });
  },
  retry: (sourceId: string) =>
    apiRequest<ProcessingJob>(`/sources/${sourceId}/retry`, { method: "POST" }),
  delete: (sourceId: string) =>
    apiRequest<{ deleted: boolean }>(`/sources/${sourceId}`, { method: "DELETE" }),
};

export type SourceType = "url" | "text" | "pdf";
export type SourceStatus = "pending" | "processing" | "ready" | "failed";
export type JobStage = "fetching" | "extracting" | "cleaning" | "chunking" | "saving" | "analyzing";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ProcessingJob = {
  id: string;
  source_id: string;
  status: JobStatus;
  stage: JobStage;
  progress: number;
  attempt_count: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
};

export type Source = {
  id: string;
  workspace_id: string;
  type: SourceType;
  url: string | null;
  title: string;
  status: SourceStatus;
  content_hash: string | null;
  language: string | null;
  created_at: string;
  updated_at: string;
  job: ProcessingJob | null;
};

export type SourceInput = {
  workspaceId: string;
  type: SourceType;
  title: string;
  url?: string;
  text?: string;
  file?: File;
};

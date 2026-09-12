import { apiRequest } from "../../shared/api/client";
import type { AIHealth, AISettings, AISettingsInput } from "../../shared/types/ai";

export const aiSettingsApi = {
  get: () => apiRequest<AISettings>("/ai/settings"),
  update: (input: AISettingsInput) =>
    apiRequest<AISettings>("/ai/settings", {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  health: () => apiRequest<AIHealth>("/ai/health"),
};


export type AIProviderName = "ollama" | "gemini";

export type AISettings = {
  provider: AIProviderName;
  base_url: string | null;
  model: string;
  embedding_model: string;
  has_api_key: boolean;
};

export type AISettingsInput = {
  provider: AIProviderName;
  base_url?: string;
  model: string;
  embedding_model: string;
  api_key?: string;
};

export type AIHealth = {
  available: boolean;
  provider: string;
  model: string;
};


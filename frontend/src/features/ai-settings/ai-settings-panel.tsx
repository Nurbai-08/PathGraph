import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, Cpu, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { aiSettingsApi } from "../../entities/ai-settings/api";
import { ApiError } from "../../shared/api/client";
import type { AIProviderName, AISettings, AISettingsInput } from "../../shared/types/ai";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { Input } from "../../shared/ui/input";
import { ErrorMessage } from "../../shared/ui/status";

export function AISettingsPanel() {
  useLocale();
  const settings = useQuery({ queryKey: ["ai-settings"], queryFn: aiSettingsApi.get, retry: false });
  if (settings.isLoading) return <p className="mt-8 text-sm text-ink/45">{t("Loading AI settings…")}</p>;

  const isMissing = settings.error instanceof ApiError && settings.error.status === 404;
  if (settings.isError && !isMissing) {
    return <div className="mt-8"><ErrorMessage message={t("Could not load AI settings.")} /></div>;
  }
  return <AISettingsForm initial={settings.data ?? null} />;
}

function AISettingsForm({ initial }: { initial: AISettings | null }) {
  useLocale();
  const [provider, setProvider] = useState<AIProviderName>(initial?.provider ?? "gemini");
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? "http://localhost:11434");
  const [model, setModel] = useState(initial?.model ?? "gemini-flash-lite-latest");
  const [embeddingModel, setEmbeddingModel] = useState(
    initial?.embedding_model ?? "gemini-embedding-001",
  );
  const [apiKey, setApiKey] = useState("");
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: aiSettingsApi.update,
    onSuccess: (value) => {
      queryClient.setQueryData(["ai-settings"], value);
      setApiKey("");
      health.reset();
    },
  });
  const health = useMutation({ mutationFn: aiSettingsApi.health });

  function chooseProvider(value: AIProviderName) {
    setProvider(value);
    if (value === "ollama") {
      setModel("gemma3");
      setEmbeddingModel("embeddinggemma");
    } else {
      setModel("gemini-flash-lite-latest");
      setEmbeddingModel("gemini-embedding-001");
    }
    health.reset();
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const input: AISettingsInput = { provider, model, embedding_model: embeddingModel };
    if (provider === "ollama") input.base_url = baseUrl;
    if (provider === "gemini" && apiKey) input.api_key = apiKey;
    save.mutate(input);
  }

  const saveError = save.error instanceof ApiError ? save.error.message : save.error?.message;
  return (
    <Card className="mt-8 p-6 sm:p-8">
      <div className="flex items-center gap-4">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-moss/10 text-moss">
          <Cpu size={22} />
        </span>
        <div>
          <h2 className="font-semibold">{t("AI provider")}</h2>
          <p className="mt-1 text-sm text-ink/50">{t("Used for concept extraction and embeddings")}</p>
        </div>
      </div>

      <p className="mt-5 text-sm text-ink/65">{t("Russian source → Russian graph. English source → Russian and English.")}</p>
      <p className="mt-3 text-sm text-ink/65">{t("Firebase handles sign-in only. Gemini needs a separate Google AI Studio key, or run Ollama locally.")}</p>
      {provider === "gemini" && <a className="mt-2 inline-block text-sm font-semibold text-moss underline" href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">{t("Get a Gemini API key")}</a>}

      <form className="mt-8 space-y-5" onSubmit={submit}>
        <div className="grid grid-cols-2 gap-3">
          {(["ollama", "gemini"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => chooseProvider(value)}
              className={`rounded-2xl border px-4 py-4 text-left transition ${
                provider === value ? "border-moss bg-moss/5" : "border-ink/10 hover:border-ink/25"
              }`}
            >
              <span className="flex items-center gap-2 font-semibold capitalize">
                <Sparkles size={16} className="text-moss" /> {value}
              </span>
              <span className="mt-1 block text-xs text-ink/45">
                {value === "ollama" ? t("Private and local") : t("Google cloud API")}
              </span>
            </button>
          ))}
        </div>
        {provider === "ollama" && (
          <label className="block space-y-2 text-sm font-medium"> {t("Base URL")} <Input required type="url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          </label>
        )}
        {provider === "gemini" && (
          <label className="block space-y-2 text-sm font-medium"> {t("API key")} <Input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={initial?.has_api_key ? t("Saved securely · leave blank to keep") : t("Required")}
              required={!initial?.has_api_key}
              autoComplete="off"
            />
          </label>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-2 text-sm font-medium"> {t("Generation model")} <Input required value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label className="block space-y-2 text-sm font-medium"> {t("Embedding model")} <Input
              required
              value={embeddingModel}
              onChange={(event) => setEmbeddingModel(event.target.value)}
            />
          </label>
        </div>
        {saveError && <ErrorMessage message={saveError} />}
        {save.isSuccess && <p className="text-sm text-moss">{t("Settings saved. Test the connection, then return to the material and run AI analysis.")}</p>}
        {health.error && <ErrorMessage message={health.error.message} />}
        {health.data && (
          <p className={`flex items-center gap-2 text-sm font-medium ${health.data.available ? "text-moss" : "text-red-700"}`}>
            {health.data.available ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
            {health.data.available ? t("Provider is available") : t("Provider is unavailable")}
          </p>
        )}
        <div className="flex flex-wrap justify-end gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={() => health.mutate()}
            disabled={!initial || health.isPending}
          >
            {health.isPending ? t("Checking…") : t("Test connection")}
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? t("Saving…") : t("Save AI settings")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

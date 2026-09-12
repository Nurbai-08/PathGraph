import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { conceptApi } from "../../entities/concept/api";
import { learningApi } from "../../entities/learning/api";
import { sourceApi } from "../../entities/source/api";
import { t, useLocale } from "../../shared/lib/i18n";
import type { LearningConcept } from "../../shared/types/learning";
import { Button } from "../../shared/ui/button";
import { ErrorMessage } from "../../shared/ui/status";

export function StudyConcept({ conceptId }: { conceptId: string }) {
  useLocale();
  const client = useQueryClient();
  const concept = useQuery({ queryKey: ["concept", conceptId], queryFn: () => conceptApi.detail(conceptId) });
  const update = useMutation({
    mutationFn: (status: LearningConcept["status"]) => learningApi.setStatus(conceptId, status),
    onSuccess: async () => {
      await Promise.all(["concept", "graph", "learning-paths", "next-concept"].map((key) =>
        client.invalidateQueries({ queryKey: [key] })));
    },
  });
  return <div className="space-y-3 border-t border-ink/10 pt-4">
    <p className="font-semibold">{t("Study material")}</p>
    {concept.isError && <ErrorMessage message={concept.error.message} />}
    {concept.data?.sources.map((source) => <SourceReader key={source.id} sourceId={source.id} title={source.title} />)}
    <label className="block text-sm">{t("My progress")}
      <select className="mt-2 w-full rounded-xl border border-ink/20 bg-white p-2" disabled={update.isPending || !concept.data}
        value={concept.data?.knowledge_status ?? "unseen"}
        onChange={(event) => update.mutate(event.target.value as LearningConcept["status"])}>
        {(["unseen", "learning", "understood", "mastered"] as const).map((status) =>
          <option key={status} value={status}>{t(status)}</option>)}
      </select>
    </label>
    {update.error && <ErrorMessage message={update.error.message} />}
  </div>;
}

export function SourceReader({ sourceId, title }: { sourceId: string; title: string }) {
  useLocale();
  const [open, setOpen] = useState(false);
  const source = useQuery({ queryKey: ["source-detail", sourceId], queryFn: () => sourceApi.detail(sourceId), enabled: open });
  return <div>
    <Button variant="secondary" className="h-auto text-left" onClick={() => setOpen(!open)}>{t(open ? "Hide material" : "Read material")}: {title}</Button>
    {open && <div className="mt-3 max-h-96 overflow-auto rounded-xl bg-cream p-3 text-sm">
      {source.isLoading && <p>{t("Loading…")}</p>}
      {source.error && <ErrorMessage message={source.error.message} />}
      {source.data?.url && <a className="font-semibold text-moss underline" href={source.data.url} target="_blank" rel="noreferrer">{t("Open original page")}</a>}
      <p className="mt-2 whitespace-pre-wrap leading-6">{source.data?.document?.clean_content ?? ""}</p>
      <p className="mt-3 text-xs text-ink/50">{t("Original text is preserved. AI explanations and translations are available after connecting a provider.")}</p>
    </div>}
  </div>;
}

import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Circle, FileText, Link2, LoaderCircle, RotateCcw, Trash2, Type } from "lucide-react";

import { sourceApi } from "./api";
import type { JobStage, Source } from "../../shared/types/source";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { SourceReader } from "../../features/learning/study-concept";
import { ErrorMessage } from "../../shared/ui/status";

const stages: JobStage[] = ["fetching", "extracting", "cleaning", "chunking", "saving", "analyzing"];
const icons = { url: Link2, text: Type, pdf: FileText };

export function SourceCard({ source, onOpenGraph }: { source: Source; onOpenGraph?: () => void }) {
  useLocale();
  const queryClient = useQueryClient();
  const refresh = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["sources", source.workspace_id] }),
    queryClient.invalidateQueries({ queryKey: ["graph", source.workspace_id] }),
    queryClient.invalidateQueries({ queryKey: ["learning-paths", source.workspace_id] }),
  ]);
  const retry = useMutation({ mutationFn: () => sourceApi.retry(source.id), onSuccess: refresh });
  const remove = useMutation({ mutationFn: () => sourceApi.delete(source.id), onSuccess: refresh });
  const Icon = icons[source.type];

  return (
    <Card className="p-5 shadow-none">
      <div className="flex items-start gap-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-moss/10 text-moss">
          <Icon size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{source.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-ink/40">{t(source.type)}</p>
            </div>
            <Button
              variant="ghost"
              className="h-9 w-9 shrink-0 p-0 text-ink/40 hover:text-red-700"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
            >
              <Trash2 size={16} /><span className="sr-only">{t("Delete source")}</span>
            </Button>
          </div>

          {source.status === "ready" && (
            <p className="mt-4 flex items-center gap-2 text-sm font-medium text-moss">
              <Check size={16} /> {t("Processed and added to the graph")} </p>
          )}
          {onOpenGraph && <Button variant="secondary" className="mt-3 h-9" onClick={onOpenGraph}>{t("Open graph")}</Button>}
          {source.status === "ready" && <div className="mt-3 space-y-3">
            <SourceReader sourceId={source.id} title={source.title} />
          </div>}
          {(retry.error || remove.error) && <ErrorMessage message={(retry.error || remove.error)!.message} />}
          {(source.status === "pending" || source.status === "processing") && (
            <ProcessingStages current={source.job?.stage ?? "fetching"} />
          )}
          {source.status === "failed" && (
            <div className="mt-4 rounded-2xl bg-red-50 p-4">
              <p className="text-sm font-semibold text-red-800">{t("Processing failed")}</p>
              <p className="mt-1 text-xs leading-5 text-red-700/75">
                {t(source.job?.error_message ?? "The source could not be processed.")}
              </p>
              <Button
                variant="secondary"
                className="mt-3 h-9 px-4"
                onClick={() => retry.mutate()}
                disabled={retry.isPending}
              >
                <RotateCcw size={14} /> {t("Retry")} </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function ProcessingStages({ current }: { current: JobStage }) {
  useLocale();
  const currentIndex = stages.indexOf(current);
  return (
    <div className="mt-4 grid gap-2 sm:grid-cols-3">
      {stages.map((stage, index) => (
        <div key={stage} className="flex items-center gap-1.5 text-xs capitalize text-ink/45">
          {index < currentIndex ? (
            <Check size={13} className="text-moss" />
          ) : index === currentIndex ? (
            <LoaderCircle size={13} className="animate-spin text-moss" />
          ) : (
            <Circle size={11} />
          )}
          {t(stage)}
        </div>
      ))}
    </div>
  );
}

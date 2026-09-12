import { lazy, Suspense } from "react";

import { Card } from "../shared/ui/card";
import { t, useLocale } from "../shared/lib/i18n";

const Graph = lazy(() =>
  import("./knowledge-graph").then((module) => ({ default: module.KnowledgeGraph })),
);

export function LazyKnowledgeGraph({ workspaceId, sourceId }: { workspaceId: string; sourceId?: string }) {
  useLocale();
  return (
    <Suspense
      fallback={
        <Card className="mt-12 h-80 animate-pulse border-dashed bg-white/50 p-10 text-center text-sm text-ink/40">
          {t("Loading knowledge graph…")}
        </Card>
      }
    >
      <Graph key={`${workspaceId}:${sourceId ?? "all"}`} workspaceId={workspaceId} sourceId={sourceId} />
    </Suspense>
  );
}

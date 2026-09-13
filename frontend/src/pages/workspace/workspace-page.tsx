import { t, useLocale } from "../../shared/lib/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FilePlus2 } from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { sourceApi } from "../../entities/source/api";
import { SourceCard } from "../../entities/source/source-card";
import { workspaceApi } from "../../entities/workspace/api";
import { AddSourceModal } from "../../features/add-source/add-source-modal";
import { DeleteWorkspaceButton } from "../../features/delete-workspace/delete-workspace-button";
import { Card } from "../../shared/ui/card";
import { ErrorMessage } from "../../shared/ui/status";
import { LazyKnowledgeGraph } from "../../widgets/knowledge-graph-lazy";
import { LearningPanel } from "../../widgets/learning-panel";

export function WorkspacePage() {
  useLocale();
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const selectedSource = params.get("source") || undefined;
  const queryClient = useQueryClient();
  const workspace = useQuery({
    queryKey: ["workspace", id],
    queryFn: () => workspaceApi.get(id),
    enabled: Boolean(id),
  });
  const sources = useQuery({
    queryKey: ["sources", id],
    queryFn: () => sourceApi.list(id),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.some((source) => ["pending", "processing"].includes(source.status))
        ? 1_500
        : false,
  });
  const readySourceIds = sources.data
    ?.filter((source) => source.status === "ready")
    .map((source) => source.id)
    .sort()
    .join(":");
  const graphEmptyMessage = getGraphEmptyMessage(sources.data);

  useEffect(() => {
    if (readySourceIds === undefined) return;
    void queryClient.invalidateQueries({ queryKey: ["graph", id] });
  }, [id, queryClient, readySourceIds]);

  useEffect(() => {
    if (!selectedSource || !sources.data) return;
    if (!sources.data.some((source) => source.id === selectedSource)) {
      setParams({}, { replace: true });
    }
  }, [selectedSource, setParams, sources.data]);

  if (workspace.isError) return <ErrorMessage message={t("Workspace could not be found.")} />;
  if (!workspace.data) return <p className="text-sm text-ink/50">{t("Loading workspace…")}</p>;

  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-2 text-sm font-medium text-ink/50 hover:text-moss">
        <ArrowLeft size={16} /> {t("All workspaces")} </Link>
      <div className="mt-8 flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("Workspace")}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{workspace.data.name}</h1>
          {workspace.data.description && <p className="mt-3 max-w-2xl text-ink/55">{workspace.data.description}</p>}
        </div>
        <div className="flex flex-wrap gap-3">
          <AddSourceModal workspaceId={id} onAdded={(sourceId) => setParams({ source: sourceId })} />
          <DeleteWorkspaceButton
            workspaceId={id}
            workspaceName={workspace.data.name}
            onDeleted={() => navigate("/")}
          />
        </div>
      </div>
      {sources.data?.length === 0 && (
        <Card className="mt-10 border-dashed bg-white/60 p-10 text-center sm:p-16">
          <FilePlus2 className="mx-auto text-moss" size={36} />
          <h2 className="mt-5 text-2xl font-semibold">{t("No knowledge yet.")}</h2>
          <p className="mt-2 text-sm text-ink/50">{t("Add a URL, plain text, or PDF to get started.")}</p>
        </Card>
      )}
      {sources.data && sources.data.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-ink/45">{t("Sources")}</h2>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {sources.data.map((source) => <SourceCard key={source.id} source={source} onOpenGraph={() => {
              setParams({ source: source.id });
              document.getElementById("source-graph")?.scrollIntoView({ behavior: "smooth" });
            }} />)}
          </div>
        </section>
      )}
      <LearningPanel workspaceId={id} />
      <section id="source-graph" className="mt-8 scroll-mt-4">
        <label className="flex flex-wrap items-center gap-3 text-sm font-semibold">
          {t("Graph material")}
          <select className="max-w-full rounded-xl border border-ink/20 bg-white p-3" value={selectedSource ?? ""}
            onChange={(event) => setParams(event.target.value ? { source: event.target.value } : {})}>
            <option value="">{t("All materials — combined graph")}</option>
            {sources.data?.map((source) => <option key={source.id} value={source.id}>{source.title}</option>)}
          </select>
        </label>
        <LazyKnowledgeGraph
          workspaceId={id}
          sourceId={sources.data?.some((source) => source.id === selectedSource) ? selectedSource : undefined}
          emptyMessage={graphEmptyMessage}
        />
      </section>
    </div>
  );
}

function getGraphEmptyMessage(sources: Awaited<ReturnType<typeof sourceApi.list>> | undefined): string {
  if (!sources?.length) return "Add a source to build your knowledge graph.";
  if (sources.some((source) => source.status === "pending" || source.status === "processing")) {
    return "The material is being analyzed. The graph will appear when processing is complete.";
  }
  if (sources.every((source) => source.status === "failed")) {
    return "The materials could not be analyzed. Review the error above and retry.";
  }
  return "No learning concepts were found in these materials. Add a specific lesson or article.";
}

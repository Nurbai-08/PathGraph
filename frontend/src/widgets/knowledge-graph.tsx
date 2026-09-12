import { t, useLocale } from "../shared/lib/i18n";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "@xyflow/react";
import { useQuery } from "@tanstack/react-query";
import { Network, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { conceptApi } from "../entities/concept/api";
import { ConceptInsights, GraphAssistant } from "../features/ai-interactions/ai-interactions";
import type { GraphEdge, GraphNode } from "../shared/types/graph";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { AIRequired } from "../features/ai-settings/ai-required";
import { StudyConcept } from "../features/learning/study-concept";

type ConceptNodeData = {
  label: string;
  conceptType: string;
  importance: number;
  mastery: number;
};

export function KnowledgeGraph({ workspaceId, sourceId }: { workspaceId: string; sourceId?: string }) {
  useLocale();
  const [focusId, setFocusId] = useState<string>();
  const [selectedId, setSelectedId] = useState<string>();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const graph = useQuery({
    queryKey: ["graph", workspaceId, sourceId, focusId],
    queryFn: () => conceptApi.graph(workspaceId, focusId, sourceId),
  });
  const results = useQuery({
    queryKey: ["concept-search", workspaceId, search],
    queryFn: () => conceptApi.search(workspaceId, search),
    enabled: !sourceId && search.trim().length >= 2,
  });
  const searchResults = sourceId
    ? graph.data?.nodes.filter((node) => node.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
    : results.data;

  const types = useMemo(
    () => [...new Set(graph.data?.nodes.map((node) => node.type) ?? [])].sort(),
    [graph.data],
  );
  const visible = useMemo(() => {
    const nodes = graph.data?.nodes.filter((node) => filter === "all" || node.type === filter) ?? [];
    const ids = new Set(nodes.map((node) => node.id));
    const edges = graph.data?.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)) ?? [];
    return { nodes, edges };
  }, [filter, graph.data]);

  if (graph.isLoading) return <GraphPlaceholder message={t("Loading knowledge graph…")} />;
  if (graph.isError) return <GraphPlaceholder message={t("The graph could not be loaded.")} />;
  if (graph.data?.nodes.length === 0) {
    return <GraphPlaceholder message={t("Concepts will appear after a source is analyzed with your AI provider.")} />;
  }

  function chooseConcept(conceptId: string) {
    setFocusId(conceptId);
    setSelectedId(conceptId);
    setSearch("");
  }

  return (
    <section className="mt-12">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("Knowledge map")}</p>
          <h2 className="mt-2 text-2xl font-semibold">{t("Interactive Graph")}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            className="h-10 rounded-full border border-ink/15 bg-white px-4 text-sm outline-none"
          >
            <option value="all">{t("All types")}</option>
            {types.map((type) => <option key={type} value={type}>{t(type)}</option>)}
          </select>
          {focusId && <Button variant="secondary" className="h-10" onClick={() => setFocusId(undefined)}>{t("Overview")}</Button>}
        </div>
      </div>

      <div className="relative mt-5">
        <div className="absolute left-4 top-4 z-10 w-[min(20rem,calc(100%-2rem))]">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-ink/35" size={16} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("Search concepts")}
              className="h-10 w-full rounded-full border border-ink/15 bg-white pl-9 pr-9 text-sm shadow-sm outline-none focus:border-moss"
            />
            {search && (
              <button className="absolute right-3 top-3 text-ink/35" onClick={() => setSearch("")}>
                <X size={16} /><span className="sr-only">{t("Clear search")}</span>
              </button>
            )}
          </div>
          {searchResults && search && (
            <Card className="mt-2 overflow-hidden rounded-2xl py-1 shadow-soft">
              {searchResults.length === 0 && <p className="px-4 py-3 text-sm text-ink/45">{t("No concepts found")}</p>}
              {searchResults.map((result) => (
                <button
                  key={result.id}
                  onClick={() => chooseConcept(result.id)}
                  className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-cream"
                >
                  <span className="font-medium">{result.name}</span>
                  <span className="text-xs text-ink/40">{t(result.type)}</span>
                </button>
              ))}
            </Card>
          )}
        </div>
        <GraphCanvas
          key={visible.nodes.map((node) => node.id).join(":")}
          graphNodes={visible.nodes}
          graphEdges={visible.edges}
          onSelect={setSelectedId}
        />
        {selectedId && <ConceptPanel conceptId={selectedId} onClose={() => setSelectedId(undefined)} />}
      </div>
      {graph.data?.truncated && (
        <p className="mt-3 text-xs text-ink/45">{t("Showing a focused subset for smooth performance.")}</p>
      )}
      {graph.data?.nodes.some((node) => node.type === "demo_concept") && (
        <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{t("Demo graph: headings and keywords only. Connect AI in Settings for translation and semantic analysis.")}</p>
      )}
      <AIRequired><GraphAssistant workspaceId={workspaceId} nodes={graph.data?.nodes ?? []} /></AIRequired>
    </section>
  );
}

function GraphCanvas({
  graphNodes,
  graphEdges,
  onSelect,
}: {
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  onSelect: (conceptId: string) => void;
}) {
  const { locale } = useLocale();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<ConceptNodeData>>(
    layoutNodes(graphNodes),
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(mapEdges(graphEdges));
  const handleClick: NodeMouseHandler<Node<ConceptNodeData>> = (_event, node) => onSelect(node.id);

  useEffect(() => {
    setNodes((currentNodes) => preserveNodePositions(currentNodes, layoutNodes(graphNodes)));
  }, [graphNodes, setNodes, locale]);

  useEffect(() => {
    setEdges(mapEdges(graphEdges));
  }, [graphEdges, setEdges, locale]);

  return (
    <Card className="h-[36rem] overflow-hidden bg-[#fbfaf5] p-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleClick}
        fitView
        minZoom={0.2}
        maxZoom={2}
      >
        <Background color="#245c3f" gap={24} size={1} />
        <Controls />
        <MiniMap pannable zoomable nodeColor="#c9f27b" maskColor="rgba(246,244,236,.72)" />
      </ReactFlow>
    </Card>
  );
}

function ConceptPanel({ conceptId, onClose }: { conceptId: string; onClose: () => void }) {
  useLocale();
  const concept = useQuery({
    queryKey: ["concept", conceptId],
    queryFn: () => conceptApi.detail(conceptId),
  });
  return (
    <Card className="absolute bottom-4 right-4 top-4 z-10 w-[min(22rem,calc(100%-2rem))] overflow-auto rounded-2xl p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-moss">{t(concept.data?.type ?? "")}</p>
          <h3 className="mt-2 text-2xl font-semibold">{concept.data?.name ?? t("Loading…")}</h3>
        </div>
        <Button variant="ghost" className="h-8 w-8 p-0" onClick={onClose}><X size={16} /></Button>
      </div>
      {concept.data && (
        <div className="mt-5 space-y-5 text-sm">
          <p className="whitespace-pre-wrap leading-6 text-ink/60">{concept.data.description || t("No description yet.")}</p>
          <div>
            <p className="font-semibold capitalize">{t(concept.data.knowledge_status)}</p>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink/10">
              <div className="h-full rounded-full bg-moss" style={{ width: `${concept.data.mastery}%` }} />
            </div>
            <p className="mt-1 text-xs text-ink/45">{t("Mastery")} {concept.data.mastery}%</p>
          </div>
          <ConceptLinks title={t("Prerequisites")} items={concept.data.prerequisites} />
          <ConceptLinks title={t("Unlocks")} items={concept.data.unlocks} />
          <div>
            <p className="font-semibold">{t("Sources")}</p>
            <p className="mt-1 text-ink/50">{concept.data.sources.length} {t("supporting source(s)")}</p>
          </div>
          <StudyConcept conceptId={conceptId} />
          <AIRequired><ConceptInsights key={conceptId} conceptId={conceptId} /></AIRequired>
        </div>
      )}
    </Card>
  );
}

function ConceptLinks({ title, items }: { title: string; items: Array<{ id: string; name: string }> }) {
  useLocale();
  return (
    <div>
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-ink/50">{items.length ? items.map((item) => item.name).join(", ") : t("None")}</p>
    </div>
  );
}

function layoutNodes(nodes: GraphNode[]): Array<Node<ConceptNodeData>> {
  const radius = Math.max(180, nodes.length * 16);
  return nodes.map((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    return {
      id: node.id,
      data: {
        label: `${node.name} · ${node.mastery}%`,
        conceptType: node.type,
        importance: node.importance,
        mastery: node.mastery,
      },
      position: { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius },
      style: {
        border: node.knowledge_gap ? "2px solid #b42318" : "1px solid rgba(36,92,63,.25)",
        borderRadius: 18,
        background: masteryColor(node.mastery),
        color: node.mastery >= 85 ? "#fff" : "#17211b",
        fontWeight: 600,
        padding: 12,
        width: 150,
      },
    };
  });
}

function preserveNodePositions(
  currentNodes: Array<Node<ConceptNodeData>>,
  nextNodes: Array<Node<ConceptNodeData>>,
): Array<Node<ConceptNodeData>> {
  const positions = new Map(currentNodes.map((node) => [node.id, node.position]));
  return nextNodes.map((node) => ({
    ...node,
    position: positions.get(node.id) ?? node.position,
  }));
}

function masteryColor(mastery: number): string {
  if (mastery >= 85) return "#17452f";
  if (mastery >= 60) return "#a7d8a0";
  if (mastery > 0) return "#f6c77a";
  return "#e7e8e4";
}

function mapEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: t(edge.type),
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#769280" },
    labelStyle: { fill: "#506359", fontSize: 10 },
  }));
}

function GraphPlaceholder({ message }: { message: string }) {
  useLocale();
  return (
    <Card className="mt-12 border-dashed bg-white/60 p-10 text-center">
      <Network className="mx-auto text-moss" size={30} />
      <p className="mt-4 text-sm text-ink/50">{message}</p>
    </Card>
  );
}

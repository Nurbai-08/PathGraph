export type GraphNode = {
  id: string;
  name: string;
  type: string;
  mastery: number;
  importance: number;
  knowledge_gap: boolean;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
};

export type KnowledgeGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
};

export type ConceptSummary = {
  id: string;
  name: string;
  type: string;
};

export type ConceptDetail = {
  id: string;
  name: string;
  type: string;
  description: string;
  importance: number;
  confidence: number;
  mastery: number;
  knowledge_status: string;
  aliases: string[];
  prerequisites: ConceptSummary[];
  unlocks: ConceptSummary[];
  sources: Array<{ id: string; title: string; type: string }>;
};

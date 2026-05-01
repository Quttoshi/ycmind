const BASE_URL = "";

export interface Citation {
  entity_name: string;
  entity_type: string;
  relevance: string;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphContext {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  graph_context: GraphContext;
  retrieval_method: "graph" | "vector" | "hybrid";
  latency_ms: number;
}

export async function submitQuery(question: string, topK = 5): Promise<QueryResponse> {
  const res = await fetch(`${BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function getSubgraph(entity: string, depth = 2): Promise<GraphContext> {
  const res = await fetch(
    `${BASE_URL}/graph?entity=${encodeURIComponent(entity)}&depth=${depth}`
  );
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

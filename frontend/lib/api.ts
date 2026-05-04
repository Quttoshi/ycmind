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

export interface StreamDoneMeta {
  retrieval_method: "graph" | "vector" | "hybrid";
  latency_ms: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  citations: Citation[];
}

export async function streamQuery(
  question: string,
  topK = 5,
  callbacks: {
    onToken: (token: string) => void;
    onDone: (meta: StreamDoneMeta) => void;
    onError: (err: string) => void;
  }
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
    });
  } catch (e) {
    callbacks.onError(e instanceof Error ? e.message : "Network error");
    return;
  }

  if (!res.ok) {
    callbacks.onError(`API error ${res.status}: ${await res.text()}`);
    return;
  }

  if (!res.body) {
    callbacks.onError("Response has no body");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;
        try {
          const event = JSON.parse(raw);
          if (event.type === "token" && event.content) {
            callbacks.onToken(event.content);
          } else if (event.type === "done") {
            callbacks.onDone({
              retrieval_method: event.retrieval_method,
              latency_ms: event.latency_ms,
              nodes: event.nodes ?? [],
              edges: event.edges ?? [],
              citations: event.citations ?? [],
            });
          } else if (event.type === "error") {
            callbacks.onError(event.message ?? "Unknown stream error");
          }
        } catch {
          // malformed SSE line — skip
        }
      }
    }
  } catch (e) {
    callbacks.onError(e instanceof Error ? e.message : "Stream reading failed");
  }
}

export async function getSubgraph(entity: string, depth = 2): Promise<GraphContext> {
  const res = await fetch(
    `${BASE_URL}/graph?entity=${encodeURIComponent(entity)}&depth=${depth}`
  );
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

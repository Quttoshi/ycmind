"use client";

import ReactMarkdown from "react-markdown";
import { Citation, QueryResponse } from "@/lib/api";

const METHOD_COLORS: Record<string, string> = {
  hybrid: "bg-blue-100 text-blue-700",
  graph: "bg-green-100 text-green-700",
  vector: "bg-amber-100 text-amber-700",
};

const ENTITY_COLORS: Record<string, string> = {
  Company: "bg-blue-50 text-blue-700 border-blue-200",
  Founder: "bg-green-50 text-green-700 border-green-200",
  Batch: "bg-amber-50 text-amber-700 border-amber-200",
  Sector: "bg-violet-50 text-violet-700 border-violet-200",
};

interface Props {
  response: QueryResponse;
}

export default function AnswerPanel({ response }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {/* Metadata row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${METHOD_COLORS[response.retrieval_method] || "bg-gray-100 text-gray-600"}`}
        >
          {response.retrieval_method}
        </span>
        <span className="text-xs text-gray-400">{response.latency_ms}ms</span>
        <span className="text-xs text-gray-400">
          {response.graph_context.nodes.length} nodes ·{" "}
          {response.graph_context.edges.length} edges
        </span>
      </div>

      {/* Answer */}
      <div className="prose prose-sm max-w-none text-gray-800">
        <ReactMarkdown>{response.answer}</ReactMarkdown>
      </div>

      {/* Citations */}
      {response.citations.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">Sources</p>
          <div className="flex flex-wrap gap-2">
            {response.citations.map((c, i) => (
              <span
                key={i}
                title={c.relevance}
                className={`rounded border px-2 py-0.5 text-xs ${ENTITY_COLORS[c.entity_type] || "bg-gray-50 text-gray-600 border-gray-200"}`}
              >
                {c.entity_name}
                <span className="ml-1 opacity-60 text-[10px]">{c.entity_type}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

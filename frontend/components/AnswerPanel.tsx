"use client";

import ReactMarkdown from "react-markdown";
import { QueryResponse } from "@/lib/api";

const METHOD_COLORS: Record<string, string> = {
  hybrid: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  graph: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  vector: "text-amber-400 bg-amber-500/10 border-amber-500/20",
};

const ENTITY_COLORS: Record<string, string> = {
  Company: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  Founder: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  Batch: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  Sector: "text-violet-400 bg-violet-500/10 border-violet-500/20",
};

interface Props {
  response?: QueryResponse;
  streamingAnswer?: string;
  isStreaming?: boolean;
}

export default function AnswerPanel({ response, streamingAnswer = "", isStreaming = false }: Props) {
  const displayText = response ? streamingAnswer || response.answer : streamingAnswer;

  return (
    <div className="flex flex-col gap-4">
      {/* Meta — only show when retrieval is complete */}
      {response && (
        <div className="flex items-center gap-3">
          <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${METHOD_COLORS[response.retrieval_method] || "text-white/40 bg-white/5 border-white/10"}`}>
            {response.retrieval_method}
          </span>
          <span className="text-xs text-white/25">{response.latency_ms}ms</span>
          <span className="text-white/10">·</span>
          <span className="text-xs text-white/25">
            {response.graph_context.nodes.length} nodes · {response.graph_context.edges.length} edges
          </span>
        </div>
      )}

      {/* Answer text */}
      <div className="prose prose-sm prose-invert max-w-none text-white/80 prose-headings:text-white prose-a:text-orange-400 prose-strong:text-white prose-p:leading-relaxed">
        <ReactMarkdown>{displayText}</ReactMarkdown>
        {isStreaming && (
          <span className="inline-block w-0.5 h-4 bg-orange-400 ml-0.5 align-middle animate-pulse" />
        )}
      </div>

      {/* Citations */}
      {response && response.citations.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-3">
            Sources
          </p>
          <div className="flex flex-wrap gap-1.5">
            {response.citations.map((c, i) => (
              <span
                key={i}
                title={c.relevance}
                className={`rounded-full border px-3 py-0.5 text-xs font-medium ${ENTITY_COLORS[c.entity_type] || "text-white/40 bg-white/5 border-white/10"}`}
              >
                {c.entity_name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

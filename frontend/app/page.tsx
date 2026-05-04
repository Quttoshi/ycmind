"use client";

import { useState, useRef } from "react";
import { streamQuery, QueryResponse } from "@/lib/api";
import SearchBar, { SearchBarHandle } from "@/components/SearchBar";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsTable from "@/components/ResultsTable";
import FollowUps from "@/components/FollowUps";
import Sidebar from "@/components/Sidebar";
import { Network, Sparkles } from "lucide-react";

// ─── Static suggestion data (all queries are real API calls) ─────────────────

const QUICK_CHIPS = [
  { icon: "✅", label: "Active",    query: "Show me active YC companies" },
  { icon: "🤝", label: "Acquired",  query: "Show me all YC companies that were acquired" },
  { icon: "🦓", label: "Stripe",    query: "Tell me about Stripe" },
  { icon: "🏠", label: "Airbnb",    query: "What does Airbnb do?" },
];

const EXAMPLE_QUERIES = [
  "Find all YC fintech companies",
  "Find companies building AI tools for developers",
  "Companies solving healthcare access in emerging markets",
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home() {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const searchRef = useRef<SearchBarHandle>(null);

  const handleSubmit = async (question: string) => {
    setIsLoading(true);
    setIsStreaming(false);
    setStreamingAnswer("");
    setError(null);
    setResponse(null);
    setLastQuery(question);

    await streamQuery(question, 5, {
      onToken: (token) => {
        setIsLoading(false);
        setIsStreaming(true);
        setStreamingAnswer((prev) => prev + token);
      },
      onDone: (meta) => {
        setIsStreaming(false);
        setResponse({
          answer: "",
          citations: meta.citations,
          graph_context: { nodes: meta.nodes, edges: meta.edges },
          retrieval_method: meta.retrieval_method,
          latency_ms: meta.latency_ms,
        });
        setIsLoading(false);
      },
      onError: (err) => {
        setError(err);
        setIsLoading(false);
        setIsStreaming(false);
      },
    });
  };

  const handleNewSearch = () => {
    setResponse(null);
    setError(null);
    setLastQuery("");
    setStreamingAnswer("");
    setIsStreaming(false);
    setIsLoading(false);
    setTimeout(() => searchRef.current?.focus(), 50);
  };

  const hasResult = response !== null || isLoading || isStreaming || streamingAnswer !== "" || error !== null;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* Sidebar */}
      <Sidebar
        currentQuery={lastQuery}
        onNewSearch={handleNewSearch}
        onSelectHistory={handleSubmit}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((v) => !v)}
      />

      {/* Main — flex column so content scrolls above fixed bottom bar */}
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden">
        {!hasResult ? (
          /* ── HERO ─────────────────────────────────────────────────────────── */
          <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8">
            <div className="flex flex-col items-center gap-2">
              <Sparkles size={28} className="text-orange-400 mb-1" />
              <h1 className="text-5xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
                YcMind
              </h1>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                GraphRAG over 4,000+ YC companies
              </p>
            </div>

            <SearchBar ref={searchRef} onSubmit={handleSubmit} isLoading={isLoading} hero />

            <div className="w-full max-w-[680px] flex flex-col gap-4">
              <div className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                <Network size={14} />
                <span className="text-sm">Try asking</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {QUICK_CHIPS.map(({ icon, label, query }) => (
                  <button
                    key={label}
                    onClick={() => handleSubmit(query)}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-full border text-sm transition-all duration-150 disabled:opacity-40 hover:opacity-80"
                    style={{ background: "var(--bg-chip)", borderColor: "var(--border)", color: "var(--text-sub)" }}
                  >
                    <span>{icon}</span>
                    <span>{label}</span>
                  </button>
                ))}
              </div>
              <div className="flex flex-col">
                {EXAMPLE_QUERIES.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSubmit(s)}
                    disabled={isLoading}
                    className="flex items-center gap-3 py-2.5 text-sm text-left border-b transition-colors disabled:opacity-40 group"
                    style={{ color: "var(--text-muted)", borderColor: "var(--border)" }}
                  >
                    <span className="text-xs shrink-0 group-hover:text-orange-400 transition-colors" style={{ color: "var(--text-muted)" }}>→</span>
                    <span className="group-hover:text-[var(--text-sub)] transition-colors">{s}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* ── RESULTS ─────────────────────────────────────────────────────── */
          <>
            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-[720px] mx-auto w-full px-6 pt-8 pb-6">
                {lastQuery && (
                  <h2 className="text-xl font-semibold mb-5 leading-snug" style={{ color: "var(--text)" }}>
                    {lastQuery}
                  </h2>
                )}

                {isLoading && (
                  <div className="flex items-center gap-3 py-4 text-sm" style={{ color: "var(--text-muted)" }}>
                    <span className="h-1.5 w-1.5 rounded-full bg-orange-400 animate-ping" />
                    <span className="h-1.5 w-1.5 rounded-full bg-orange-400 animate-ping [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-orange-400 animate-ping [animation-delay:300ms]" />
                    <span className="ml-1">Traversing knowledge graph…</span>
                  </div>
                )}

                {error && (
                  <div className="mb-5 rounded-xl border border-red-500/20 bg-red-500/10 px-5 py-4 text-sm text-red-400">
                    {error}
                  </div>
                )}

                {(isStreaming || (streamingAnswer && !response)) && (
                  <AnswerPanel streamingAnswer={streamingAnswer} isStreaming={isStreaming} />
                )}

                {response && (
                  <div className="flex flex-col gap-3">
                    <AnswerPanel response={response} streamingAnswer={streamingAnswer} isStreaming={false} />
                    <ResultsTable nodes={response.graph_context.nodes} />
                    <FollowUps query={lastQuery} onSelect={handleSubmit} />
                  </div>
                )}
              </div>
            </div>

            {/* Fixed bottom search bar */}
            <div className="shrink-0 px-6 py-4" style={{ background: "var(--bg)" }}>
              <div className="max-w-[720px] mx-auto">
                <SearchBar ref={searchRef} onSubmit={handleSubmit} isLoading={isLoading} />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

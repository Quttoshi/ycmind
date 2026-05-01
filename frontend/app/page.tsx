"use client";

import { useState, useRef } from "react";
import { submitQuery, QueryResponse } from "@/lib/api";
import SearchBar, { SearchBarHandle } from "@/components/SearchBar";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsTable from "@/components/ResultsTable";
import FollowUps from "@/components/FollowUps";

export default function Home() {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const searchRef = useRef<SearchBarHandle>(null);


  const handleSubmit = async (question: string) => {
    setIsLoading(true);
    setError(null);
    setResponse(null);
    setLastQuery(question);
    try {
      const result = await submitQuery(question);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  const hasResult = response || isLoading || error;

  return (
    <div className="min-h-screen bg-[#111111] text-white">
      {/* Sticky header after query */}
      {hasResult && (
        <header className="sticky top-0 z-10 border-b border-white/5 bg-[#111111]/90 backdrop-blur-md">
          <div className="mx-auto max-w-2xl px-6 py-3 flex items-center gap-3">
            <button
              onClick={() => { setResponse(null); setError(null); setLastQuery(""); }}
              className="text-base font-semibold text-orange-400 hover:text-orange-300 transition-colors shrink-0"
            >
              YcMind
            </button>
            <span className="text-white/15">·</span>
            <span className="text-sm text-white/30 truncate">{lastQuery}</span>
          </div>
        </header>
      )}

      <main className="mx-auto max-w-2xl px-6">
        {/* Hero */}
        {!hasResult && (
          <div className="flex flex-col items-center pt-40 pb-10 gap-8">
            <div className="flex flex-col items-center gap-2">
              <h1 className="text-5xl font-semibold tracking-tight bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">
                YcMind
              </h1>
              <p className="text-sm text-white/30">GraphRAG over 4,000+ YC companies</p>
            </div>
            <SearchBar ref={searchRef} onSubmit={handleSubmit} isLoading={isLoading} hero />
          </div>
        )}

        {/* Compact search */}
        {hasResult && (
          <div className="py-5">
            <SearchBar ref={searchRef} onSubmit={handleSubmit} isLoading={isLoading} />
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center gap-2 pb-6 text-sm text-white/30">
            <span className="h-1 w-1 rounded-full bg-orange-400 animate-ping" />
            <span className="h-1 w-1 rounded-full bg-orange-400 animate-ping [animation-delay:200ms]" />
            <span className="h-1 w-1 rounded-full bg-orange-400 animate-ping [animation-delay:400ms]" />
            <span className="ml-2">Traversing knowledge graph...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-500/20 bg-red-500/10 px-5 py-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Results */}
        {response && (
          <div className="flex flex-col gap-3 pb-16">
            <AnswerPanel response={response} />
            <ResultsTable nodes={response.graph_context.nodes} />
            <FollowUps query={lastQuery} onSelect={handleSubmit} />
          </div>
        )}
      </main>
    </div>
  );
}

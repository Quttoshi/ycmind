"use client";

import { useState } from "react";
import { submitQuery, QueryResponse } from "@/lib/api";
import SearchBar from "@/components/SearchBar";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsTable from "@/components/ResultsTable";

export default function Home() {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (question: string) => {
    setIsLoading(true);
    setError(null);
    setResponse(null);
    try {
      const result = await submitQuery(question);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4 flex items-center gap-3">
          <span className="text-2xl font-bold text-orange-500">ycmind</span>
          <span className="text-sm text-gray-400">
            GraphRAG over 4,000+ YC companies
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 flex flex-col gap-8">
        {/* Search */}
        <SearchBar onSubmit={handleSubmit} isLoading={isLoading} />

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-orange-400 border-t-transparent" />
            Traversing knowledge graph...
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {response && (
          <div className="flex flex-col gap-6">
            <div className="rounded-lg border border-gray-200 bg-white px-6 py-5">
              <AnswerPanel response={response} />
            </div>
            <ResultsTable nodes={response.graph_context.nodes} />
          </div>
        )}

        {/* Empty state */}
        {!response && !isLoading && !error && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white px-6 py-12 text-center">
            <p className="text-sm text-gray-400">
              Ask a multi-hop question about YC companies, founders, batches, or sectors.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

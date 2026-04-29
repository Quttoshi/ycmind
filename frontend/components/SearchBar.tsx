"use client";

import { FormEvent, KeyboardEvent, useState } from "react";

const EXAMPLE_QUERIES = [
  "Which W23 fintech founders previously worked at Goldman Sachs?",
  "Find all YC DevTools companies from the S21 batch",
  "Which Stanford founders built companies in the AI sector?",
  "Show me all YC companies that have been acquired",
];

interface Props {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

export default function SearchBar({ onSubmit, isLoading }: Props) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim() && !isLoading) onSubmit(question.trim());
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (question.trim() && !isLoading) onSubmit(question.trim());
    }
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about YC companies and founders..."
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
          disabled={isLoading}
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">⌘ + Enter to submit</span>
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            className="rounded-lg bg-orange-500 px-5 py-2 text-sm font-medium text-white hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Thinking..." : "Ask"}
          </button>
        </div>
      </form>

      <div className="mt-4">
        <p className="text-xs text-gray-400 mb-2">Example queries</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => setQuestion(q)}
              className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:border-orange-400 hover:text-orange-600 transition-colors"
            >
              {q.length > 50 ? q.slice(0, 50) + "…" : q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

"use client";

import { FormEvent, KeyboardEvent, useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";

const EXAMPLE_QUERIES = [
  { icon: "💰", label: "YC fintech companies", q: "Find all YC fintech companies" },
  { icon: "🤝", label: "Acquired companies", q: "Show me all YC companies that have been acquired" },
  { icon: "🛠️", label: "S21 DevTools", q: "Find all YC DevTools companies from the S21 batch" },
  { icon: "🎓", label: "Stanford founders", q: "Which founders studied at Stanford?" },
];

interface Props {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  hero?: boolean;
}

export interface SearchBarHandle {
  focus: () => void;
}

const SearchBar = forwardRef<SearchBarHandle, Props>(function SearchBar({ onSubmit, isLoading, hero }, ref) {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

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

  const handleChip = (q: string) => {
    setQuestion(q);
    onSubmit(q);
  };

  return (
    <div className={`flex flex-col gap-4 w-full ${hero ? "max-w-3xl mx-auto" : ""}`}>
      <form onSubmit={handleSubmit} className="relative group">
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about YC companies, founders, batches..."
          rows={hero ? 3 : 2}
          className="w-full rounded-2xl border border-white/10 bg-[#1a1a1a] px-5 py-4 pr-24 text-sm text-white/90 placeholder-white/20 resize-none focus:outline-none focus:border-white/20 focus:bg-[#1e1e1e] transition-all duration-200"
          disabled={isLoading}
        />
        <div className="absolute bottom-3.5 right-3.5 flex items-center gap-2">
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            className="rounded-xl bg-orange-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-orange-400 active:scale-95 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-150 shadow-lg shadow-orange-500/20"
          >
            {isLoading ? "···" : "Ask"}
          </button>
        </div>
      </form>

      {hero && (
        <div className="flex flex-wrap gap-2 justify-center">
          {EXAMPLE_QUERIES.map(({ icon, label, q }) => (
            <button
              key={q}
              onClick={() => handleChip(q)}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-full border border-white/8 bg-white/[0.04] px-3.5 py-1.5 text-xs text-white/40 hover:border-white/15 hover:text-white/70 hover:bg-white/[0.07] transition-all duration-150 disabled:opacity-30"
            >
              <span>{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
});

export default SearchBar;

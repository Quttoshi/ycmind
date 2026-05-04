"use client";

import {
  FormEvent,
  KeyboardEvent,
  useState,
  useRef,
  useEffect,
  forwardRef,
  useImperativeHandle,
} from "react";
import { ArrowUp } from "lucide-react";

interface Props {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  hero?: boolean;
}

export interface SearchBarHandle {
  focus: () => void;
}

const SearchBar = forwardRef<SearchBarHandle, Props>(function SearchBar(
  { onSubmit, isLoading, hero },
  ref
) {
  const [question, setQuestion] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

  const doSubmit = () => {
    const q = question.trim();
    if (q && !isLoading) {
      onSubmit(q);
      setQuestion("");
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    doSubmit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      doSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [question]);

  const canSubmit = question.trim().length > 0 && !isLoading;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-[780px]">
      <div
        className="flex flex-col rounded-3xl border transition-colors duration-150"
        style={{
          background: "var(--bg-input)",
          borderColor: isFocused ? "var(--border-focus)" : "var(--border)",
        }}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Ask about YC companies, founders, batches..."
          rows={hero ? 3 : 2}
          style={{
            minHeight: hero ? 100 : 60,
            maxHeight: 200,
            resize: "none",
            background: "transparent",
            outline: "none",
          }}
          className="w-full px-5 pt-5 pb-2 text-sm text-white/90 placeholder-white/40 overflow-hidden"
          disabled={isLoading}
          aria-label="Search query"
        />

        {/* Submit row */}
        <div className="flex items-center justify-end px-3 pb-3 pt-1">
          <span className="flex-1 text-xs text-white/40 px-1">
            {"Enter to send · Shift+Enter for newline"}
          </span>
          <button
            type="submit"
            disabled={!canSubmit}
            aria-label="Submit search"
            className={`flex items-center justify-center w-7 h-7 rounded-full transition-all duration-150 active:scale-95 ${
              canSubmit
                ? "text-white hover:opacity-90"
                : "text-[var(--text-muted)] cursor-not-allowed"
            }`}
            style={
              canSubmit
                ? {
                    background: "var(--accent)",
                    boxShadow: "0 0 12px var(--accent-glow)",
                  }
                : { background: "var(--bg-chip)" }
            }
          >
            {isLoading ? (
              <div
                className="w-3 h-3 rounded-full border border-white/30 animate-spin"
                style={{ borderTopColor: "rgba(255,255,255,0.8)" }}
              />
            ) : (
              <ArrowUp size={13} />
            )}
          </button>
        </div>
      </div>
    </form>
  );
});

export default SearchBar;

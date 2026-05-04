"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  Clock,
} from "lucide-react";

interface SidebarProps {
  currentQuery: string;
  onNewSearch: () => void;
  onSelectHistory: (q: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({
  currentQuery,
  onNewSearch,
  onSelectHistory,
  isCollapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [history, setHistory] = useState<string[]>([]);

  // Load history from localStorage (client-only)
  useEffect(() => {
    try {
      const stored = localStorage.getItem("ycmind-history");
      if (stored) setHistory(JSON.parse(stored) as string[]);
    } catch {
      // ignore parse errors
    }
  }, []);

  // Append new query to history on each submission
  useEffect(() => {
    if (!currentQuery) return;
    setHistory((prev) => {
      const next = [
        currentQuery,
        ...prev.filter((q) => q !== currentQuery),
      ].slice(0, 10);
      try {
        localStorage.setItem("ycmind-history", JSON.stringify(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  }, [currentQuery]);

  return (
    <aside
      style={{ width: isCollapsed ? 56 : 208, background: "var(--bg-surface)" }}
      className="hidden lg:flex flex-col shrink-0 h-screen sticky top-0 overflow-hidden border-r border-[var(--border)] transition-all duration-200"
    >
      {/* Logo row */}
      <div className={`flex items-center px-3 py-3 min-h-[52px] ${isCollapsed ? "justify-center" : "justify-between"}`}>
        {!isCollapsed && (
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles size={15} className="text-orange-400 shrink-0" />
            <span className="text-sm font-semibold text-[var(--text)] truncate">
              YcMind
            </span>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md text-white/50 hover:text-white/75 hover:bg-[var(--bg-hover)] transition-all shrink-0"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <PanelLeftOpen size={15} />
          ) : (
            <PanelLeftClose size={15} />
          )}
        </button>
      </div>

      {/* New search */}
      <div className="px-2 pt-1">
        <button
          onClick={onNewSearch}
          title={isCollapsed ? "New search" : undefined}
          className={`flex items-center gap-2.5 w-full rounded-lg px-2.5 py-2 text-sm text-white/75 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all ${
            isCollapsed ? "justify-center" : ""
          }`}
        >
          <Plus size={15} className="shrink-0" />
          {!isCollapsed && <span>New</span>}
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-2 pt-5 pb-2 min-h-0">
        {!isCollapsed && (
          <>
            <div className="flex items-center gap-1.5 px-2.5 mb-2">
              <Clock size={11} className="text-white/50" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-white/50">
                History
              </span>
            </div>

            {history.length === 0 ? (
              <p className="px-2.5 text-xs text-white/50">
                No recent searches
              </p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {history.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => onSelectHistory(q)}
                    title={q}
                    className="w-full text-left rounded-lg px-2.5 py-1.5 text-xs text-white/50 hover:text-white/75 hover:bg-[var(--bg-hover)] transition-all truncate"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}

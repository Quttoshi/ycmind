"use client";

interface Props {
  query: string;
  onSelect: (q: string) => void;
}

function generateFollowUps(query: string): string[] {
  const q = query.toLowerCase();
  if (q.includes("fintech") || q.includes("finance")) {
    return [
      "Which fintech YC companies went public?",
      "Find YC fintech companies from the W21 batch",
      "Show me acquired fintech YC startups",
    ];
  }
  if (q.includes("acquired")) {
    return [
      "Which acquired YC companies were in fintech?",
      "Show me YC companies that went public",
      "Find acquired YC companies from the S20 batch",
    ];
  }
  if (q.includes("stanford") || q.includes("university") || q.includes("founder")) {
    return [
      "Which MIT founders built YC companies?",
      "Find founders who previously worked at Google",
      "Show me YC companies with solo founders",
    ];
  }
  return [
    "Find all YC fintech companies",
    "Show me YC companies that went public",
    "Which YC companies are from the W23 batch?",
  ];
}

export default function FollowUps({ query, onSelect }: Props) {
  const suggestions = generateFollowUps(query);

  return (
    <div className="pt-2">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-3">
        Follow-up
      </p>
      <div className="flex flex-col">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSelect(s)}
            className="flex items-center gap-2 text-left text-sm text-white/40 hover:text-white/80 py-2 border-b border-white/5 last:border-0 transition-colors group"
          >
            <span className="text-white/15 group-hover:text-orange-500 transition-colors shrink-0">→</span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

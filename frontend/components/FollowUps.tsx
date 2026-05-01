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
  if (q.includes("devtools") || q.includes("developer") || q.includes("saas")) {
    return [
      "Find YC AI companies from S23",
      "Show me YC infrastructure companies",
      "Which DevTools companies were acquired?",
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
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-6 py-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-3">
        Follow-up
      </p>
      <div className="flex flex-col gap-1">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSelect(s)}
            className="flex items-center gap-2 text-left text-sm text-white/40 hover:text-white/80 py-1.5 transition-colors group"
          >
            <span className="text-white/15 group-hover:text-orange-500 transition-colors">→</span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

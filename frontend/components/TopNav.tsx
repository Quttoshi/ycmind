"use client";

interface TopNavProps {
  categories: string[];
  activeCategory: string;
  onSelect: (cat: string) => void;
}

export default function TopNav({
  categories,
  activeCategory,
  onSelect,
}: TopNavProps) {
  return (
    <nav
      className="flex items-center justify-center gap-1 px-4 py-2.5 border-b border-[var(--border)] shrink-0"
      aria-label="Category navigation"
    >
      {categories.map((cat) => (
        <button
          key={cat}
          onClick={() => onSelect(cat)}
          className={`px-3.5 py-1.5 text-sm rounded-full transition-all duration-150 ${
            activeCategory === cat
              ? "text-[var(--text)] font-medium"
              : "text-[var(--text-muted)] hover:text-[var(--text-sub)]"
          }`}
        >
          {cat}
        </button>
      ))}
    </nav>
  );
}

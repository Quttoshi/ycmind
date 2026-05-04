"use client";

import { GraphNode } from "@/lib/api";

interface Props {
  nodes: GraphNode[];
}

const STATUS_COLORS: Record<string, string> = {
  Active: "text-emerald-400 bg-emerald-500/10",
  Acquired: "text-blue-400 bg-blue-500/10",
  Inactive: "text-white/30 bg-white/5",
  Public: "text-violet-400 bg-violet-500/10",
};

export default function ResultsTable({ nodes }: Props) {
  const companies = nodes.filter((n) => n.label === "Company");
  const founders = nodes.filter((n) => n.label === "Founder");

  if (nodes.length === 0) return null;

  return (
    <div className="flex flex-col gap-6">
      {companies.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-3">
            Companies · {companies.length}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] font-semibold uppercase tracking-widest text-white/20 border-b border-white/5">
                  <th className="pb-2 text-left pr-6">Company</th>
                  <th className="pb-2 text-left pr-6">Batch</th>
                  <th className="pb-2 text-left pr-6">Status</th>
                  <th className="pb-2 text-left">Description</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((node, i) => {
                  const p = node.properties;
                  const status = String(p.status || "");
                  return (
                    <tr key={node.id} className={`hover:bg-white/[0.02] transition-colors ${i !== companies.length - 1 ? "border-b border-white/5" : ""}`}>
                      <td className="py-2.5 pr-6 font-medium text-white/80">
                        {p.url ? (
                          <a href={String(p.url)} target="_blank" rel="noopener noreferrer" className="hover:text-orange-400 transition-colors">
                            {String(p.name || "")} <span className="text-white/20 text-xs">↗</span>
                          </a>
                        ) : String(p.name || "")}
                      </td>
                      <td className="py-2.5 pr-6">
                        {p.batch ? <span className="font-mono text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded">{String(p.batch)}</span> : <span className="text-white/15">—</span>}
                      </td>
                      <td className="py-2.5 pr-6">
                        {status ? <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] || "text-white/30 bg-white/5"}`}>{status}</span> : <span className="text-white/15">—</span>}
                      </td>
                      <td className="py-2.5 text-white/35 text-xs max-w-xs truncate">{String(p.one_liner || "—")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {founders.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-3">
            Founders · {founders.length}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] font-semibold uppercase tracking-widest text-white/20 border-b border-white/5">
                  <th className="pb-2 text-left pr-6">Name</th>
                  <th className="pb-2 text-left pr-6">Role</th>
                  <th className="pb-2 text-left pr-6">University</th>
                  <th className="pb-2 text-left">Previously at</th>
                </tr>
              </thead>
              <tbody>
                {founders.map((node, i) => {
                  const p = node.properties;
                  return (
                    <tr key={node.id} className={`hover:bg-white/[0.02] transition-colors ${i !== founders.length - 1 ? "border-b border-white/5" : ""}`}>
                      <td className="py-2.5 pr-6 font-medium text-white/80">
                        {p.linkedin_url ? (
                          <a href={String(p.linkedin_url)} target="_blank" rel="noopener noreferrer" className="hover:text-orange-400 transition-colors">
                            {String(p.name || "")} <span className="text-white/20 text-xs">↗</span>
                          </a>
                        ) : String(p.name || "")}
                      </td>
                      <td className="py-2.5 pr-6 text-white/35 text-xs">{String(p.role || "—")}</td>
                      <td className="py-2.5 pr-6 text-white/35 text-xs">{String(p.university || "—")}</td>
                      <td className="py-2.5 text-white/35 text-xs">{String(p.previous_company || "—")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

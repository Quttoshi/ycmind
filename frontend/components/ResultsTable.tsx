"use client";

import { GraphNode } from "@/lib/api";

interface Props {
  nodes: GraphNode[];
}

const STATUS_COLORS: Record<string, string> = {
  Active: "bg-green-100 text-green-700",
  Acquired: "bg-blue-100 text-blue-700",
  Inactive: "bg-gray-100 text-gray-500",
  Public: "bg-purple-100 text-purple-700",
};

export default function ResultsTable({ nodes }: Props) {
  const companies = nodes.filter((n) => n.label === "Company");
  const founders = nodes.filter((n) => n.label === "Founder");

  if (nodes.length === 0) return null;

  return (
    <div className="flex flex-col gap-6">
      {/* Companies table */}
      {companies.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Companies ({companies.length})
          </h3>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Company</th>
                  <th className="px-4 py-2 text-left">Batch</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">One-liner</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {companies.map((node) => {
                  const p = node.properties;
                  const status = String(p.status || "");
                  return (
                    <tr key={node.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2 font-medium text-gray-900">
                        {p.url ? (
                          <a
                            href={String(p.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-orange-600 hover:underline"
                          >
                            {String(p.name || "")}
                          </a>
                        ) : (
                          String(p.name || "")
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-500">{String(p.batch || "—")}</td>
                      <td className="px-4 py-2">
                        {status && (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status] || "bg-gray-100 text-gray-600"}`}
                          >
                            {status}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-500 max-w-xs truncate">
                        {String(p.one_liner || "—")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Founders table */}
      {founders.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Founders ({founders.length})
          </h3>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Role</th>
                  <th className="px-4 py-2 text-left">University</th>
                  <th className="px-4 py-2 text-left">Previously at</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {founders.map((node) => {
                  const p = node.properties;
                  return (
                    <tr key={node.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2 font-medium text-gray-900">
                        {p.linkedin_url ? (
                          <a
                            href={String(p.linkedin_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-orange-600 hover:underline"
                          >
                            {String(p.name || "")}
                          </a>
                        ) : (
                          String(p.name || "")
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-500">{String(p.role || "—")}</td>
                      <td className="px-4 py-2 text-gray-500">{String(p.university || "—")}</td>
                      <td className="px-4 py-2 text-gray-500">{String(p.previous_company || "—")}</td>
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

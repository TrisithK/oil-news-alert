"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tierLabel, timeAgo } from "@/lib/format";
import type { Source } from "@/lib/types";

export function SourcesTable() {
  const [sources, setSources] = useState<Source[]>([]);

  const load = () => api.sources().then(setSources).catch(() => undefined);
  useEffect(() => {
    load();
  }, []);

  const toggle = async (s: Source) => {
    await api.patchSource(s.id, { enabled: !s.enabled }).catch(() => undefined);
    load();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Sources</h1>
      <div className="overflow-x-auto rounded-xl border border-ink-700">
        <table className="w-full text-sm">
          <thead className="bg-ink-900 text-left text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="p-3">Source</th>
              <th className="p-3">Kind</th>
              <th className="p-3">Tier</th>
              <th className="p-3">Interval</th>
              <th className="p-3">Last fetched</th>
              <th className="p-3 text-right">Enabled</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id} className="border-t border-ink-800 align-top">
                <td className="p-3">
                  <div className="text-slate-200">{s.name}</div>
                  {s.url && <div className="max-w-xs truncate text-xs text-slate-600">{s.url}</div>}
                </td>
                <td className="p-3 font-mono text-xs text-slate-400">{s.kind}</td>
                <td className="p-3">
                  <span className="rounded bg-ink-700 px-1.5 py-0.5 text-xs text-slate-300">
                    {tierLabel(s.reliability_tier)}
                  </span>
                </td>
                <td className="p-3 text-slate-400">{Math.round(s.poll_interval_sec / 60)}m</td>
                <td className="p-3 text-slate-400">
                  {s.last_fetched_at ? timeAgo(s.last_fetched_at) : "—"}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => toggle(s)}
                    aria-label={s.enabled ? "disable" : "enable"}
                    className={`relative inline-block h-5 w-9 rounded-full transition ${
                      s.enabled ? "bg-bull" : "bg-ink-600"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                        s.enabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

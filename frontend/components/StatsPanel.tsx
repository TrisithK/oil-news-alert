"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { categoryLabel, directionStyle } from "@/lib/format";
import type { Stats } from "@/lib/types";

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-2xl text-white">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function BarRow({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <div className="w-36 shrink-0 truncate text-slate-400">{label}</div>
      <div className="h-3 flex-1 overflow-hidden rounded bg-ink-800">
        <div className={`h-full ${color}`} style={{ width: `${(value / max) * 100}%` }} />
      </div>
      <div className="w-8 text-right font-mono text-xs text-slate-300">{value}</div>
    </div>
  );
}

export function StatsPanel() {
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => {
    api.stats().then(setS).catch(() => undefined);
  }, []);

  if (!s) return <p className="text-slate-500">Loading stats…</p>;

  const catMax = Math.max(1, ...Object.values(s.by_category));
  const dirMax = Math.max(1, ...Object.values(s.by_direction));
  const tta = s.avg_time_to_alert_sec != null ? `${(s.avg_time_to_alert_sec / 60).toFixed(1)}m` : "—";
  const feedbackTotal = Object.values(s.feedback_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Stats</h1>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Articles" value={String(s.total_articles)} />
        <Kpi
          label="Relevant signals"
          value={String(s.relevant_analyses)}
          sub={`of ${s.total_analyses} analyzed`}
        />
        <Kpi label="Alerts fired" value={String(s.total_alerts)} />
        <Kpi label="Avg importance" value={s.avg_importance?.toFixed(1) ?? "—"} />
        <Kpi label="Avg time-to-alert" value={tta} />
        <Kpi
          label="Feedback useful"
          value={s.feedback_useful_ratio != null ? `${Math.round(s.feedback_useful_ratio * 100)}%` : "—"}
          sub={`${feedbackTotal} responses`}
        />
        <Kpi label="Prompt tokens" value={s.total_prompt_tokens.toLocaleString()} />
        <Kpi label="Completion tokens" value={s.total_completion_tokens.toLocaleString()} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <div className="mb-3 text-sm font-medium">Signals by category</div>
          <div className="space-y-1.5">
            {Object.entries(s.by_category)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => (
                <BarRow key={k} label={categoryLabel(k)} value={v} max={catMax} color="bg-brand-500" />
              ))}
          </div>
        </div>
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <div className="mb-3 text-sm font-medium">Signals by direction</div>
          <div className="space-y-1.5">
            {Object.entries(s.by_direction)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => (
                <BarRow
                  key={k}
                  label={directionStyle(k).label}
                  value={v}
                  max={dirMax}
                  color={k === "bullish" ? "bg-bull" : k === "bearish" ? "bg-bear" : "bg-slate-500"}
                />
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

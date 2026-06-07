"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FeedDetail, ScoreBreakdown } from "@/lib/types";

const WEIGHTS: { key: keyof ScoreBreakdown; label: string; weight: number }[] = [
  { key: "category_weight", label: "Event category", weight: 0.35 },
  { key: "magnitude", label: "Magnitude", weight: 0.2 },
  { key: "confidence", label: "Model confidence", weight: 0.15 },
  { key: "source_tier", label: "Source tier", weight: 0.15 },
  { key: "novelty", label: "Novelty", weight: 0.15 },
];

export function WhyScore({ id }: { id: number }) {
  const [detail, setDetail] = useState<FeedDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .feedItem(id)
      .then((d) => active && setDetail(d))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [id]);

  if (error) return <div className="mt-3 text-xs text-bear">Failed to load breakdown.</div>;
  if (!detail) return <div className="mt-3 text-xs text-slate-500">Loading breakdown…</div>;

  const b = detail.score_breakdown;
  return (
    <div className="mt-3 space-y-3 rounded-lg border border-ink-700 bg-ink-950/60 p-3 text-sm">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">
        Why this score — models suggest, the formula decides
      </div>
      <div className="space-y-1.5">
        {WEIGHTS.map((w) => {
          const value = b[w.key];
          const contribution = w.weight * value * 100;
          return (
            <div key={w.key} className="flex items-center gap-3">
              <div className="w-32 shrink-0 text-slate-400">{w.label}</div>
              <div className="h-2 flex-1 overflow-hidden rounded bg-ink-800">
                <div className="h-full bg-brand-500" style={{ width: `${value * 100}%` }} />
              </div>
              <div className="w-9 text-right font-mono text-xs text-slate-500">{value.toFixed(2)}</div>
              <div className="w-14 text-right font-mono text-xs text-slate-300">
                +{contribution.toFixed(1)}
              </div>
            </div>
          );
        })}
      </div>
      {b.surprise_factor !== 1 && (
        <div className="text-xs text-slate-400">
          × surprise factor {b.surprise_factor.toFixed(2)} (scheduled data)
        </div>
      )}
      <div className="flex items-center justify-between border-t border-ink-700 pt-2">
        <span className="text-slate-400">Importance score</span>
        <span className="font-mono text-lg text-white">{b.importance_score.toFixed(1)}</span>
      </div>
      {detail.rationale && <p className="leading-relaxed text-slate-300">{detail.rationale}</p>}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span>triage: {detail.model_triage ?? "—"}</span>
        <span>extract: {detail.model_extract ?? "—"}</span>
        <span>
          tokens: {detail.prompt_tokens ?? 0}/{detail.completion_tokens ?? 0}
        </span>
        {detail.key_entities && detail.key_entities.length > 0 && (
          <span>entities: {detail.key_entities.join(", ")}</span>
        )}
      </div>
    </div>
  );
}

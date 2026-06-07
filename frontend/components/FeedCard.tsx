"use client";

import { useState } from "react";
import {
  categoryLabel,
  directionStyle,
  importanceBadge,
  tierLabel,
  timeAgo,
} from "@/lib/format";
import type { FeedItem } from "@/lib/types";
import { WhyScore } from "./WhyScore";

export function FeedCard({ item, isNew }: { item: FeedItem; isNew?: boolean }) {
  const [open, setOpen] = useState(false);
  const dir = directionStyle(item.expected_direction);
  const badge = importanceBadge(item.importance_score);

  return (
    <article
      className={`rounded-xl border border-ink-700 bg-ink-850 p-4 ${isNew ? "animate-flash" : ""}`}
    >
      <div className="flex items-start gap-4">
        <div className="flex w-12 shrink-0 flex-col items-center">
          <div className="font-mono text-2xl leading-none text-white">
            {Math.round(item.importance_score ?? 0)}
          </div>
          <span
            className={`mt-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ring-1 ${badge.className}`}
          >
            {badge.label}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className={`font-semibold ${dir.className}`}>
              {dir.symbol} {dir.label}
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-300">{categoryLabel(item.event_category)}</span>
            {item.time_horizon && (
              <>
                <span className="text-slate-600">·</span>
                <span className="text-slate-400">{item.time_horizon}</span>
              </>
            )}
          </div>

          <h3 className="mt-1 font-medium leading-snug text-slate-100">
            {item.headline_summary || item.title}
          </h3>

          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            {(item.instruments_affected ?? []).map((i) => (
              <span key={i} className="rounded bg-ink-700 px-1.5 py-0.5 font-mono text-slate-300">
                {i}
              </span>
            ))}
            <span className="text-slate-500">
              {item.source_name ?? "—"} · {tierLabel(item.source_tier)}
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-500">{timeAgo(item.created_at)}</span>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="text-brand-400 hover:underline"
              >
                source ↗
              </a>
            )}
            <button
              onClick={() => setOpen((o) => !o)}
              className="ml-auto rounded border border-ink-600 px-2 py-0.5 text-slate-300 transition hover:bg-ink-700"
            >
              {open ? "Hide" : "Why this score"}
            </button>
          </div>

          {open && <WhyScore id={item.id} />}
        </div>
      </div>
    </article>
  );
}

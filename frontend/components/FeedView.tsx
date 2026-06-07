"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FeedItem, StreamAlert, StreamAnalysis } from "@/lib/types";
import { FeedCard } from "./FeedCard";
import { FilterBar, type Filters } from "./FilterBar";

export function FeedView() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [filters, setFilters] = useState<Filters>({ min_importance: 0, instrument: "", category: "" });
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const [live, setLive] = useState(false);
  const [toast, setToast] = useState<StreamAlert | null>(null);

  const load = useCallback(async () => {
    const page = await api.feed({ limit: 80 });
    setItems(page.items);
  }, []);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  useEffect(() => {
    const es = new EventSource(api.streamUrl());
    es.addEventListener("heartbeat", () => setLive(true));
    es.addEventListener("analysis", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as StreamAnalysis;
      api
        .feedItem(data.id)
        .then((item) => {
          setItems((prev) => (prev.some((p) => p.id === item.id) ? prev : [item, ...prev]));
          setNewIds((prev) => new Set(prev).add(item.id));
          setTimeout(() => {
            setNewIds((prev) => {
              const next = new Set(prev);
              next.delete(item.id);
              return next;
            });
          }, 2200);
        })
        .catch(() => undefined);
    });
    es.addEventListener("alert", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as StreamAlert;
      setToast(data);
      setTimeout(() => setToast(null), 6500);
    });
    es.onerror = () => setLive(false);
    return () => es.close();
  }, []);

  // Apply filters client-side so SSE-prepended items respect them too.
  const visible = items.filter(
    (it) =>
      (it.importance_score ?? 0) >= filters.min_importance &&
      (!filters.instrument || (it.instruments_affected ?? []).includes(filters.instrument)) &&
      (!filters.category || it.event_category === filters.category),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Live Feed</h1>
          <p className="text-xs text-slate-500">
            {visible.length} of {items.length} analyzed items shown
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span
            className={`h-2 w-2 rounded-full ${live ? "animate-pulse bg-bull" : "bg-slate-600"}`}
          />
          {live ? "live" : "connecting…"}
        </div>
      </div>

      <FilterBar filters={filters} onChange={setFilters} />

      <div className="space-y-3">
        {visible.length === 0 && (
          <p className="rounded-xl border border-ink-700 bg-ink-900 p-6 text-center text-slate-500">
            No analyzed items match the current filters.
          </p>
        )}
        {visible.map((it) => (
          <FeedCard key={it.id} item={it} isNew={newIds.has(it.id)} />
        ))}
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-30 w-80 rounded-xl border border-amber-500/40 bg-ink-850 p-4 shadow-2xl">
          <div className="text-xs font-semibold uppercase tracking-wide text-amber-300">
            ⚡ Alert fired
          </div>
          <div className="mt-1 text-sm text-slate-100">{toast.headline_summary}</div>
          <div className="mt-1 text-xs text-slate-400">
            importance {Math.round(toast.importance_score ?? 0)} · {toast.event_category}
          </div>
        </div>
      )}
    </div>
  );
}

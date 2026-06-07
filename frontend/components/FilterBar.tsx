"use client";

import { CATEGORIES, INSTRUMENTS } from "@/lib/format";

export interface Filters {
  min_importance: number;
  instrument: string;
  category: string;
}

export function FilterBar({
  filters,
  onChange,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl border border-ink-700 bg-ink-900 p-3">
      <label className="flex items-center gap-2 text-sm">
        <span className="text-slate-400">Min importance</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={filters.min_importance}
          onChange={(e) => onChange({ ...filters, min_importance: Number(e.target.value) })}
          className="accent-brand-500"
        />
        <span className="w-8 font-mono text-slate-200">{filters.min_importance}</span>
      </label>

      <select
        value={filters.instrument}
        onChange={(e) => onChange({ ...filters, instrument: e.target.value })}
        className="rounded border border-ink-700 bg-ink-800 px-2 py-1 text-sm"
      >
        <option value="">All instruments</option>
        {INSTRUMENTS.map((i) => (
          <option key={i} value={i}>
            {i}
          </option>
        ))}
      </select>

      <select
        value={filters.category}
        onChange={(e) => onChange({ ...filters, category: e.target.value })}
        className="rounded border border-ink-700 bg-ink-800 px-2 py-1 text-sm"
      >
        <option value="">All categories</option>
        {CATEGORIES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
    </div>
  );
}

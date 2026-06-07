"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CATEGORIES, INSTRUMENTS } from "@/lib/format";
import type { TraderConfig } from "@/lib/types";

export function ConfigForm() {
  const [cfg, setCfg] = useState<TraderConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getConfig().then(setCfg).catch(() => undefined);
  }, []);

  if (!cfg) return <p className="text-slate-500">Loading config…</p>;

  const channels = (cfg.channels ?? {}) as Record<string, unknown>;
  const quiet = (cfg.quiet_hours ?? {}) as Record<string, string>;

  const toggleArray = (field: "instruments" | "categories", value: string) => {
    const current = cfg[field] ?? [];
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    setCfg({ ...cfg, [field]: next.length ? next : null });
  };

  const setChannel = (key: string, value: unknown) =>
    setCfg({ ...cfg, channels: { ...channels, [key]: value } });

  const setQuiet = (key: string, value: string) => {
    const next = { ...quiet, [key]: value };
    const enabled = Boolean(next.start) && Boolean(next.end);
    setCfg({ ...cfg, quiet_hours: enabled ? next : null });
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.putConfig(cfg);
      setCfg(res);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Config</h1>
        <span className="text-xs text-slate-500">
          Changes apply to what gets shown and alerted.
        </span>
      </div>

      <section className="space-y-3 rounded-xl border border-ink-700 bg-ink-900 p-4">
        <label className="flex items-center gap-3">
          <span className="w-40 text-sm text-slate-400">Min importance</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={cfg.min_importance}
            onChange={(e) => setCfg({ ...cfg, min_importance: Number(e.target.value) })}
            className="flex-1 accent-brand-500"
          />
          <span className="w-10 text-right font-mono text-slate-100">{cfg.min_importance}</span>
        </label>
      </section>

      <section className="space-y-2 rounded-xl border border-ink-700 bg-ink-900 p-4">
        <div className="text-sm text-slate-400">Instruments (empty = all)</div>
        <div className="flex flex-wrap gap-2">
          {INSTRUMENTS.map((i) => {
            const on = (cfg.instruments ?? []).includes(i);
            return (
              <button
                key={i}
                onClick={() => toggleArray("instruments", i)}
                className={`rounded px-2 py-1 text-sm ${
                  on ? "bg-brand-500 text-white" : "border border-ink-600 text-slate-300 hover:bg-ink-800"
                }`}
              >
                {i}
              </button>
            );
          })}
        </div>
      </section>

      <section className="space-y-2 rounded-xl border border-ink-700 bg-ink-900 p-4">
        <div className="text-sm text-slate-400">Categories (empty = all)</div>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => {
            const on = (cfg.categories ?? []).includes(c.value);
            return (
              <button
                key={c.value}
                onClick={() => toggleArray("categories", c.value)}
                className={`rounded px-2 py-1 text-sm ${
                  on ? "bg-brand-500 text-white" : "border border-ink-600 text-slate-300 hover:bg-ink-800"
                }`}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      </section>

      <section className="space-y-2 rounded-xl border border-ink-700 bg-ink-900 p-4">
        <div className="text-sm text-slate-400">Keywords (comma-separated)</div>
        <input
          type="text"
          defaultValue={(cfg.keywords ?? []).join(", ")}
          onChange={(e) => {
            const parts = e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            setCfg({ ...cfg, keywords: parts.length ? parts : null });
          }}
          placeholder="hormuz, opec, sanctions"
          className="w-full rounded border border-ink-700 bg-ink-800 px-3 py-2 text-sm"
        />
      </section>

      <section className="grid gap-4 rounded-xl border border-ink-700 bg-ink-900 p-4 sm:grid-cols-2">
        <div className="space-y-2">
          <div className="text-sm text-slate-400">Channels</div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={channels.in_app !== false}
              onChange={(e) => setChannel("in_app", e.target.checked)}
            />
            In-app feed
          </label>
          <input
            type="text"
            defaultValue={(channels.telegram_chat_id as string) ?? ""}
            onChange={(e) => setChannel("telegram_chat_id", e.target.value || null)}
            placeholder="Telegram chat id"
            className="w-full rounded border border-ink-700 bg-ink-800 px-3 py-2 text-sm"
          />
          <input
            type="text"
            defaultValue={(channels.email as string) ?? ""}
            onChange={(e) => setChannel("email", e.target.value || null)}
            placeholder="Email address"
            className="w-full rounded border border-ink-700 bg-ink-800 px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-2">
          <div className="text-sm text-slate-400">Quiet hours (local to tz)</div>
          <div className="flex gap-2">
            <input
              type="time"
              defaultValue={quiet.start ?? ""}
              onChange={(e) => setQuiet("start", e.target.value)}
              className="rounded border border-ink-700 bg-ink-800 px-2 py-1 text-sm"
            />
            <span className="self-center text-slate-500">to</span>
            <input
              type="time"
              defaultValue={quiet.end ?? ""}
              onChange={(e) => setQuiet("end", e.target.value)}
              className="rounded border border-ink-700 bg-ink-800 px-2 py-1 text-sm"
            />
          </div>
          <input
            type="text"
            defaultValue={quiet.tz ?? "UTC"}
            onChange={(e) => setQuiet("tz", e.target.value)}
            placeholder="Timezone (e.g. Europe/London)"
            className="w-full rounded border border-ink-700 bg-ink-800 px-3 py-2 text-sm"
          />
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-400 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save config"}
        </button>
        {saved && <span className="text-sm text-bull">Saved ✓</span>}
      </div>
    </div>
  );
}

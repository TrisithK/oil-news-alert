"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { categoryLabel, directionStyle, timeAgo } from "@/lib/format";
import type { Alert } from "@/lib/types";

const LABELS = ["useful", "noise", "missed"];

export function AlertsView() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<Record<number, string>>({});

  const load = () => api.alerts().then(setAlerts).catch(() => undefined);
  useEffect(() => {
    load();
  }, []);

  const ack = async (id: number) => {
    setBusy(id);
    await api.ackAlert(id).catch(() => undefined);
    await load();
    setBusy(null);
  };

  const sendFeedback = async (id: number, label: string) => {
    await api.feedback({ alert_id: id, label }).catch(() => undefined);
    setFeedbackGiven((prev) => ({ ...prev, [id]: label }));
  };

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Alerts</h1>
      <div className="overflow-x-auto rounded-xl border border-ink-700">
        <table className="w-full text-sm">
          <thead className="bg-ink-900 text-left text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="p-3">Score</th>
              <th className="p-3">Signal</th>
              <th className="p-3">Channels</th>
              <th className="p-3">Status</th>
              <th className="p-3">Fired</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 && (
              <tr>
                <td colSpan={6} className="p-6 text-center text-slate-500">
                  No alerts yet.
                </td>
              </tr>
            )}
            {alerts.map((a) => {
              const dir = directionStyle(a.expected_direction);
              const channels =
                Object.entries(a.channels_sent ?? {})
                  .filter(([, v]) => v)
                  .map(([k]) => k)
                  .join(", ") || "—";
              return (
                <tr key={a.id} className="border-t border-ink-800 align-top">
                  <td className="p-3 font-mono text-white">{Math.round(a.importance_score ?? 0)}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className={dir.className}>{dir.symbol}</span>
                      <span className="text-slate-200">{a.headline_summary}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {categoryLabel(a.event_category)}
                      {a.url && (
                        <>
                          {" · "}
                          <a
                            href={a.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-brand-400 hover:underline"
                          >
                            source ↗
                          </a>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="p-3 text-xs text-slate-400">{channels}</td>
                  <td className="p-3">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs ${
                        a.status === "sent" ? "bg-bull/15 text-bull" : "bg-bear/15 text-bear"
                      }`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="p-3 text-xs text-slate-400">{timeAgo(a.created_at)}</td>
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-2">
                      {a.acknowledged_at ? (
                        <span className="text-xs text-slate-500">ack&rsquo;d</span>
                      ) : (
                        <button
                          onClick={() => ack(a.id)}
                          disabled={busy === a.id}
                          className="rounded border border-ink-600 px-2 py-0.5 text-xs hover:bg-ink-700"
                        >
                          Ack
                        </button>
                      )}
                      <div className="flex gap-1">
                        {LABELS.map((l) => (
                          <button
                            key={l}
                            onClick={() => sendFeedback(a.id, l)}
                            className={`rounded px-1.5 py-0.5 text-xs ${
                              feedbackGiven[a.id] === l
                                ? "bg-brand-500 text-white"
                                : "border border-ink-600 text-slate-400 hover:bg-ink-700"
                            }`}
                          >
                            {l}
                          </button>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

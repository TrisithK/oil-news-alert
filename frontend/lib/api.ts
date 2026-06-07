import type {
  Alert,
  FeedDetail,
  FeedPage,
  Source,
  Stats,
  TraderConfig,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
export const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "devtoken";

function qs(params: Record<string, unknown>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_TOKEN}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${detail}`.trim());
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface FeedParams {
  min_importance?: number;
  instrument?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  feed: (params: FeedParams = {}) =>
    req<FeedPage>(`/api/feed?${qs(params as Record<string, unknown>)}`),
  feedItem: (id: number) => req<FeedDetail>(`/api/feed/${id}`),
  alerts: () => req<Alert[]>(`/api/alerts`),
  ackAlert: (id: number) => req<Alert>(`/api/alerts/${id}/ack`, { method: "POST" }),
  feedback: (body: { alert_id: number; label: string; note?: string }) =>
    req<unknown>(`/api/feedback`, { method: "POST", body: JSON.stringify(body) }),
  getConfig: () => req<TraderConfig>(`/api/config`),
  putConfig: (body: TraderConfig) =>
    req<TraderConfig>(`/api/config`, { method: "PUT", body: JSON.stringify(body) }),
  sources: () => req<Source[]>(`/api/sources`),
  patchSource: (id: number, body: { enabled?: boolean; poll_interval_sec?: number }) =>
    req<Source>(`/api/sources/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  stats: () => req<Stats>(`/api/stats`),
  ingestRun: () => req<unknown>(`/api/ingest/run`, { method: "POST" }),
  streamUrl: () => `${API_BASE}/api/stream?token=${encodeURIComponent(API_TOKEN)}`,
};

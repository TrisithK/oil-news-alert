export interface FeedItem {
  id: number;
  article_id: number;
  created_at: string;
  importance_score: number | null;
  event_category: string | null;
  expected_direction: string | null;
  magnitude: string | null;
  confidence: number | null;
  time_horizon: string | null;
  instruments_affected: string[] | null;
  headline_summary: string | null;
  rationale: string | null;
  title: string;
  url: string;
  source_name: string | null;
  source_tier: string | null;
  published_at: string | null;
}

export interface FeedPage {
  items: FeedItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ScoreBreakdown {
  category_weight: number;
  magnitude: number;
  confidence: number;
  source_tier: number;
  novelty: number;
  surprise_factor: number;
  importance_score: number;
}

export interface FeedDetail extends FeedItem {
  novelty: number | null;
  key_entities: string[] | null;
  model_triage: string | null;
  model_extract: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  score_breakdown: ScoreBreakdown;
}

export interface Alert {
  id: number;
  analysis_id: number;
  config_id: number;
  importance_score: number | null;
  status: string;
  channels_sent: Record<string, boolean> | null;
  created_at: string;
  delivered_at: string | null;
  acknowledged_at: string | null;
  event_category: string | null;
  expected_direction: string | null;
  headline_summary: string | null;
  url: string | null;
}

export interface TraderConfig {
  id?: number;
  user_id?: number;
  name: string;
  min_importance: number;
  instruments: string[] | null;
  categories: string[] | null;
  keywords: string[] | null;
  channels: Record<string, unknown> | null;
  quiet_hours: Record<string, unknown> | null;
  enabled: boolean;
}

export interface Source {
  id: number;
  name: string;
  kind: string;
  url: string | null;
  reliability_tier: string;
  poll_interval_sec: number;
  enabled: boolean;
  last_fetched_at: string | null;
}

export interface Stats {
  total_articles: number;
  total_analyses: number;
  relevant_analyses: number;
  total_alerts: number;
  by_category: Record<string, number>;
  by_direction: Record<string, number>;
  avg_importance: number | null;
  feedback_counts: Record<string, number>;
  feedback_useful_ratio: number | null;
  avg_time_to_alert_sec: number | null;
  total_prompt_tokens: number;
  total_completion_tokens: number;
}

export interface StreamAnalysis {
  type: "analysis";
  id: number;
  importance_score: number | null;
  event_category: string | null;
  direction: string | null;
  magnitude: string | null;
  headline_summary: string | null;
  instruments: string[] | null;
  url: string | null;
  created_at: string;
}

export interface StreamAlert {
  type: "alert";
  id: number;
  importance_score: number | null;
  event_category: string | null;
  direction: string | null;
  headline_summary: string | null;
  url: string | null;
  created_at: string;
}

export const CATEGORIES: { value: string; label: string }[] = [
  { value: "opec_supply_decision", label: "OPEC+ supply" },
  { value: "geopolitics_conflict", label: "Geopolitics" },
  { value: "shipping_chokepoint", label: "Shipping chokepoint" },
  { value: "supply_outage", label: "Supply outage" },
  { value: "sanctions_embargo", label: "Sanctions" },
  { value: "inventory_data", label: "Inventory data" },
  { value: "macro_monetary", label: "Macro / monetary" },
  { value: "demand_signal", label: "Demand" },
  { value: "strategic_reserves", label: "Strategic reserves" },
  { value: "production_exports", label: "Production / exports" },
  { value: "weather", label: "Weather" },
  { value: "rumor_opinion", label: "Rumor / opinion" },
  { value: "other", label: "Other" },
];

export const INSTRUMENTS = ["BRENT", "WTI", "GASOIL", "TTF_GAS", "USD"];

export function categoryLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

export function directionStyle(direction: string | null | undefined): {
  symbol: string;
  className: string;
  label: string;
} {
  switch (direction) {
    case "bullish":
      return { symbol: "▲", className: "text-bull", label: "Bullish" };
    case "bearish":
      return { symbol: "▼", className: "text-bear", label: "Bearish" };
    case "neutral":
      return { symbol: "◆", className: "text-slate-300", label: "Neutral" };
    default:
      return { symbol: "◇", className: "text-slate-400", label: "Unclear" };
  }
}

export function importanceBadge(score: number | null | undefined): {
  className: string;
  label: string;
} {
  const s = score ?? 0;
  if (s >= 80) return { className: "bg-red-500/20 text-red-300 ring-red-500/40", label: "Critical" };
  if (s >= 65) return { className: "bg-amber-500/20 text-amber-300 ring-amber-500/40", label: "High" };
  if (s >= 45) return { className: "bg-sky-500/20 text-sky-300 ring-sky-500/40", label: "Medium" };
  return { className: "bg-slate-500/20 text-slate-300 ring-slate-500/40", label: "Low" };
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function tierLabel(tier: string | null | undefined): string {
  switch (tier) {
    case "wire":
      return "Wire";
    case "reputable":
      return "Reputable";
    case "aggregator":
      return "Aggregator";
    case "blog_social":
      return "Blog / social";
    default:
      return tier ?? "—";
  }
}

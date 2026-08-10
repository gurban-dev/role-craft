export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPercent(score?: number | null): string {
  if (score == null || Number.isNaN(score)) return "—";
  const pct = score <= 1 ? score * 100 : score;
  return `${Math.round(pct)}%`;
}

// Shapes and fetching for the athlete history endpoint (GET /api/athletes/history).

export type Meet = {
  meet: string;
  date: string | null; // "YYYY-MM-DD"; null for the handful of meets the source has no date for
  bodyweight: number | null;
  best_sn: number | null;
  best_cj: number | null;
  total: number | null;
  bombed_out: boolean;
};

export type AthleteHistory = {
  name: string;
  count: number;
  results: Meet[]; // oldest first, meets with no date last
};

export const METRICS = ["Sn", "Cj", "Total"] as const;
export type Metric = (typeof METRICS)[number];

export const METRIC_FIELD = {
  Sn: "best_sn",
  Cj: "best_cj",
  Total: "total",
} as const satisfies Record<Metric, keyof Meet>;

// Resolves to null when the API says the athlete doesn't exist; throws on any other failure.
export async function fetchHistory(name: string, signal: AbortSignal): Promise<AthleteHistory | null> {
  const res = await fetch(`/api/athletes/history?name=${encodeURIComponent(name)}`, { signal });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`history request failed: ${res.status}`);
  return res.json();
}

// Both bounds are optional "YYYY-MM-DD" strings (which compare correctly as plain strings).
// With no bounds set every meet passes, including undated ones; once a bound is set an
// undated meet can't be known to fall inside it, so it drops out.
export function filterByDateRange(results: Meet[], from: string, to: string): Meet[] {
  if (!from && !to) return results;
  return results.filter((r) => r.date && (!from || r.date >= from) && (!to || r.date <= to));
}

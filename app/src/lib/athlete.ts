// Shapes and fetching for the athlete history endpoint (GET /api/athletes/history) and the
// prediction endpoint (GET /api/athletes/predict).

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

// ---- athletes on the graph (the page's athlete, then up to MAX_COMPARED compared ones)

export type MarkerShape = "circle" | "square" | "diamond";

// One colour family per athlete, in this fixed order (requested 2026-11-08): reds/oranges/yellows, then
// greens, then blues/purples - so the page's own athlete shares the warm family with its prediction
// bands. Orange and green are hard to tell apart with red-green colour blindness (the dataviz palette
// validator passes them only with a second cue), so each athlete also gets its own marker shape.
// Each athlete's prediction bands use the same family: a darker outer band (1st-25th and 75th-99th
// percentile) and a lighter inner one (25th-75th). The page's own athlete keeps the original red/orange.
export type AthleteStyle = { color: string; shape: MarkerShape; bandOuter: string; bandInner: string };
export const ATHLETE_STYLES: AthleteStyle[] = [
  { color: "#ea580c", shape: "circle", bandOuter: "#ef4444", bandInner: "#f97316" },
  { color: "#16a34a", shape: "square", bandOuter: "#15803d", bandInner: "#4ade80" },
  { color: "#7c3aed", shape: "diamond", bandOuter: "#6d28d9", bandInner: "#60a5fa" },
];
export const MAX_COMPARED = ATHLETE_STYLES.length - 1;

export type GraphSeries = { name: string; rows: Meet[] } & AthleteStyle;

// One athlete's prediction as the graph draws it: bands from originTotal (their latest meet's total, or
// their last real one if that meet was a bomb-out) out to the predicted meet, in their colour family.
export type GraphPrediction = { name: string; prediction: Prediction; originTotal: number } & AthleteStyle;

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

// ---- prediction

// Keep in step with MAX_PREDICT_DAYS_AHEAD in app/api/index.py (the API enforces it either way; this just
// lets the page explain it before asking).
export const MAX_PREDICT_DAYS_AHEAD = 365;

// The bodyweight a prediction is made at: the athlete's last recorded one (the model barely responds to
// bodyweight, so the page no longer asks for it - removed 2026-11-08). Null if none is on record.
export function lastBodyweight(results: Meet[]): number | null {
  for (let i = results.length - 1; i >= 0; i--) {
    const r = results[i];
    if (r.date && r.bodyweight != null && r.bodyweight > 0) return r.bodyweight;
  }
  return null;
}

export type Prediction = {
  name: string;
  date: string; // the meet date that was asked about
  bodyweight: number;
  latest_meet: { date: string; total: number | null; bombed_out: boolean };
  prediction: { q1: number; q25: number; q50: number; q75: number; q99: number };
  meets_used: number;
  assumes_no_bomb_out: boolean;
};

export type PredictionResult = { ok: true; data: Prediction } | { ok: false; message: string };

// A rejected request (bad date, unknown athlete, ...) comes back as a message to show the user;
// anything unexpected throws.
export async function fetchPrediction(
  name: string,
  date: string,
  bodyweight: number,
  signal: AbortSignal,
): Promise<PredictionResult> {
  const params = new URLSearchParams({ name, date, bodyweight: String(bodyweight) });
  const res = await fetch(`/api/athletes/predict?${params}`, { signal });
  if (res.ok) return { ok: true, data: await res.json() };
  if (res.status === 404 || res.status === 422) {
    const body = await res.json().catch(() => null);
    // 422 from FastAPI's own validation carries a list rather than a string
    const message = typeof body?.detail === "string" ? body.detail : "Those values can't be used for a prediction.";
    return { ok: false, message };
  }
  throw new Error(`prediction request failed: ${res.status}`);
}

export function todayISO(): string {
  const n = new Date();
  const pad = (v: number) => String(v).padStart(2, "0");
  return `${n.getFullYear()}-${pad(n.getMonth() + 1)}-${pad(n.getDate())}`;
}

// Calendar-day arithmetic on "YYYY-MM-DD" strings, done in UTC so daylight saving can't shift a day.
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

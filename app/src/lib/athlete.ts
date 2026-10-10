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

// Keep in step with MAX_PREDICT_DAYS_AHEAD, MIN_BODYWEIGHT and MAX_BODYWEIGHT in app/api/index.py
// (the API enforces them either way; these just let the page explain them before asking).
export const MAX_PREDICT_DAYS_AHEAD = 365;
export const MIN_BODYWEIGHT = 0.1;
export const MAX_BODYWEIGHT = 299.9;

export type Prediction = {
  name: string;
  date: string; // the meet date that was asked about
  bodyweight: number;
  latest_meet: { date: string; total: number | null; bombed_out: boolean };
  prediction: { q25: number; q50: number; q75: number; q99: number };
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

// Shapes and fetching for the home page's Q-points top 10s (GET /api/rankings/q-points).

export type RankingWindow = "year" | "all";

export const WINDOW_LABELS: Record<RankingWindow, string> = { year: "Past year", all: "All time" };

export type RankingEntry = {
  rank: number;
  name: string;
  total: number;
  q_points: number;
  meet: string;
  date: string | null; // "YYYY-MM-DD"
  bodyweight: number;
};

export type Rankings = { window: RankingWindow; men: RankingEntry[]; women: RankingEntry[] };

export async function fetchRankings(window: RankingWindow, signal: AbortSignal): Promise<Rankings> {
  const res = await fetch(`/api/rankings/q-points?window=${window}`, { signal });
  if (!res.ok) throw new Error(`rankings request failed: ${res.status}`);
  return res.json();
}

// ---- distribution (GET /api/rankings/q-points/distribution)

export type Distribution = {
  athletes: number;
  bin_width: number;
  bins: { lo: number; athletes: number }[]; // lowest first, no gaps
  percentiles: { p: number; q_points: number }[]; // 25th, 50th, 75th, 90th, 99th
};

export type Distributions = { window: RankingWindow; men: Distribution; women: Distribution };

// ---- fastest improvers (GET /api/rankings/improvers)

// One athlete: their latest meet (within the past 12 months) and how many Q-points it gained over their
// best in the 12 months before it.
export type ImproverEntry = RankingEntry & { before_q_points: number; gain: number };

export type Improvers = { men: ImproverEntry[]; women: ImproverEntry[] };

export async function fetchImprovers(signal: AbortSignal): Promise<Improvers> {
  const res = await fetch("/api/rankings/improvers", { signal });
  if (!res.ok) throw new Error(`improvers request failed: ${res.status}`);
  return res.json();
}

export async function fetchDistributions(window: RankingWindow, signal: AbortSignal): Promise<Distributions> {
  const res = await fetch(`/api/rankings/q-points/distribution?window=${window}`, { signal });
  if (!res.ok) throw new Error(`distribution request failed: ${res.status}`);
  return res.json();
}

// ---- athlete counts (GET /api/stats/athletes), the bar charts at the bottom of the home page

export type AthleteStats = {
  new_per_year: { year: number; athletes: number }[]; // from 2012, when the records begin
  current_year: number; // the last year in new_per_year, still in progress
  meets_per_athlete: { meets: number; athletes: number }[]; // 1 to 30 meets
  more_meets: { athletes: number; most: number | null }; // athletes with more than 30
  athletes: number;
};

export async function fetchAthleteStats(signal: AbortSignal): Promise<AthleteStats> {
  const res = await fetch("/api/stats/athletes", { signal });
  if (!res.ok) throw new Error(`athlete stats request failed: ${res.status}`);
  return res.json();
}

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

export async function fetchDistributions(window: RankingWindow, signal: AbortSignal): Promise<Distributions> {
  const res = await fetch(`/api/rankings/q-points/distribution?window=${window}`, { signal });
  if (!res.ok) throw new Error(`distribution request failed: ${res.status}`);
  return res.json();
}

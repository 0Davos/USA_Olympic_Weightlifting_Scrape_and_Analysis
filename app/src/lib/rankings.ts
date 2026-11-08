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

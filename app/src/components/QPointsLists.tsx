"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import QPointsDistribution from "./QPointsDistribution";
import {
  fetchDistributions,
  fetchRankings,
  WINDOW_LABELS,
  type Distributions,
  type RankingEntry,
  type Rankings,
  type RankingWindow,
} from "@/lib/rankings";

// The outcome of one fetch, tagged with the request it answers (window + retry count), so switching
// windows never shows the other window's data, and "loading" is simply "no outcome for this request".
type Load<T> = { key: string; status: "ready"; data: T } | { key: string; status: "error" };

export const BOX_CLASS = "rounded-xl border border-black/10 p-6 dark:border-white/10";
export const MUTED_CLASS = "text-sm text-black/50 dark:text-white/50";
export const BAR_CLASS = "inline-block rounded bg-black/5 dark:bg-white/10";
export const ROWS = 10;

// Fetches `fetcher(period)` whenever the period or retry count changes (`fetcher` must be a stable
// function, e.g. defined at module level). Also used by FastestImprovers.
export function useLoad<T, P extends string = RankingWindow>(fetcher: (p: P, s: AbortSignal) => Promise<T>, period: P, attempt: number) {
  const [load, setLoad] = useState<Load<T> | null>(null);
  const key = `${period}#${attempt}`;
  useEffect(() => {
    const controller = new AbortController();
    fetcher(period, controller.signal)
      .then((data) => setLoad({ key, status: "ready", data }))
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoad({ key, status: "error" });
      });
    return () => controller.abort();
  }, [fetcher, period, key]);
  return load && load.key === key ? load : null;
}

// The table is always ROWS rows tall: while loading (or on an error) it shows placeholder rows with the
// same two-line layout, so the block is exactly the same size before and after the data arrives.
function RankingTable({ entries }: { entries: RankingEntry[] | null }) {
  return (
    <table className="mt-3 w-full table-fixed text-sm">
      <thead className="text-left text-xs text-black/50 dark:text-white/50">
        <tr>
          <th className="w-7 pb-2 font-normal">#</th>
          <th className="pb-2 font-normal">Athlete</th>
          <th className="w-14 pb-2 text-right font-normal">Total</th>
          <th className="w-16 pb-2 text-right font-normal">Q-points</th>
        </tr>
      </thead>
      <tbody>
        {entries
          ? entries.map((e) => (
              <tr key={e.name} className="border-t border-black/5 dark:border-white/5">
                <td className="py-1.5 text-black/50 dark:text-white/50">{e.rank}</td>
                <td className="truncate py-1.5 pr-2">
                  <Link href={`/athlete/${encodeURIComponent(e.name)}`} className="hover:underline">
                    {e.name}
                  </Link>
                  {/* The meet goes under the name: as its own column it squeezed the names to nothing. */}
                  <div className="truncate text-xs text-black/50 dark:text-white/50" title={e.meet}>
                    {e.meet}
                  </div>
                </td>
                <td className="py-1.5 text-right tabular-nums">{e.total}</td>
                <td className="py-1.5 text-right font-medium tabular-nums">{e.q_points.toFixed(1)}</td>
              </tr>
            ))
          : Array.from({ length: ROWS }, (_, i) => (
              <tr key={i} className="border-t border-black/5 dark:border-white/5" aria-hidden>
                <td className="py-1.5 text-black/30 dark:text-white/30">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  <div className="flex h-5 items-center"><span className={`${BAR_CLASS} h-3.5 w-2/3`} /></div>
                  <div className="flex h-4 items-center"><span className={`${BAR_CLASS} h-2.5 w-1/2`} /></div>
                </td>
                <td className="py-1.5 text-right"><span className={`${BAR_CLASS} h-3.5 w-8 align-middle`} /></td>
                <td className="py-1.5 text-right"><span className={`${BAR_CLASS} h-3.5 w-10 align-middle`} /></td>
              </tr>
            ))}
      </tbody>
    </table>
  );
}

// Shown over the placeholder content (which keeps the box its full size) when a fetch fails.
export function ErrorOverlay({ what, onRetry }: { what: string; onRetry: () => void }) {
  return (
    <div className={`absolute inset-0 flex flex-col items-center justify-center gap-3 ${MUTED_CLASS}`}>
      <span>Couldn&apos;t load the {what} right now.</span>
      <button type="button" onClick={onRetry} className="rounded-lg border border-black/10 px-3 py-1 dark:border-white/10">
        Try again
      </button>
    </div>
  );
}

export default function QPointsLists() {
  const [period, setPeriod] = useState<RankingWindow>("year");
  const [attempt, setAttempt] = useState(0);
  const rankings = useLoad<Rankings>(fetchRankings, period, attempt);
  const distributions = useLoad<Distributions>(fetchDistributions, period, attempt);
  const retry = () => setAttempt((a) => a + 1);

  const lists = rankings?.status === "ready" ? rankings.data : null;
  const dists = distributions?.status === "ready" ? distributions.data : null;
  const inPeriod = period === "year" ? " in the past year" : "";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Ranking period">
        {(Object.keys(WINDOW_LABELS) as RankingWindow[]).map((w) => (
          <button
            key={w}
            type="button"
            aria-pressed={period === w}
            onClick={() => setPeriod(w)}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              period === w
                ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                : "border-black/10 dark:border-white/10"
            }`}
          >
            {WINDOW_LABELS[w]}
          </button>
        ))}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {(["men", "women"] as const).map((g) => (
          <section key={g} className={`relative ${BOX_CLASS}`}>
            <h2 className="text-lg font-semibold">Top {g === "men" ? "Men" : "Women"} — Q-points</h2>
            <div className={rankings?.status === "error" ? "invisible" : ""}>
              <RankingTable entries={lists ? lists[g] : null} />
              {lists && lists[g].length === 0 && <p className={`mt-3 ${MUTED_CLASS}`}>No results in this period.</p>}
            </div>
            {rankings?.status === "error" && <ErrorOverlay what="rankings" onRetry={retry} />}
          </section>
        ))}
      </div>
      <p className="mt-3 text-xs text-black/50 dark:text-white/50">
        Each athlete&apos;s best Q-points result{inPeriod}. No age adjustment.
      </p>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        {(["men", "women"] as const).map((g) => (
          <section key={g} className={`relative ${BOX_CLASS}`}>
            <h2 className="text-lg font-semibold">{g === "men" ? "Men" : "Women"} — Q-point spread</h2>
            <p className={`mt-1 text-xs text-black/50 dark:text-white/50 ${dists ? "" : "invisible"}`}>
              {dists ? dists[g].athletes.toLocaleString() : "00,000"} athletes&apos; best results{inPeriod}
            </p>
            <div className={`mt-3 ${distributions?.status === "error" ? "invisible" : ""}`}>
              <QPointsDistribution data={dists ? dists[g] : null} id={g} />
            </div>
            {distributions?.status === "error" && <ErrorOverlay what="chart" onRetry={retry} />}
          </section>
        ))}
      </div>
    </div>
  );
}

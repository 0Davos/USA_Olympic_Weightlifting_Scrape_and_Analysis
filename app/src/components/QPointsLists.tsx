"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchRankings, WINDOW_LABELS, type RankingEntry, type Rankings, type RankingWindow } from "@/lib/rankings";

// The outcome of one fetch, tagged with the request it answers (window + retry count), so switching
// windows never shows the other window's lists, and "loading" is simply "no outcome for this request".
type Load = { key: string; status: "ready"; data: Rankings } | { key: string; status: "error" };

const BOX_CLASS = "rounded-xl border border-black/10 p-6 dark:border-white/10";
const MUTED_CLASS = "text-sm text-black/50 dark:text-white/50";

function RankingTable({ entries }: { entries: RankingEntry[] }) {
  if (entries.length === 0) return <p className={`mt-3 ${MUTED_CLASS}`}>No results in this period.</p>;
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
        {entries.map((e) => (
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
        ))}
      </tbody>
    </table>
  );
}

export default function QPointsLists() {
  const [period, setPeriod] = useState<RankingWindow>("year");
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<Load | null>(null);

  const key = `${period}#${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchRankings(period, controller.signal)
      .then((data) => setLoad({ key, status: "ready", data }))
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoad({ key, status: "error" });
      });
    return () => controller.abort();
  }, [period, key]);

  const current = load && load.key === key ? load : null;

  function body(entries: RankingEntry[] | undefined) {
    if (!current) return <p className={`mt-3 ${MUTED_CLASS}`}>Loading...</p>;
    if (current.status === "error") {
      return (
        <div className={`mt-3 flex items-center gap-3 ${MUTED_CLASS}`}>
          <span>Couldn&apos;t load the rankings right now.</span>
          <button
            type="button"
            onClick={() => setAttempt((a) => a + 1)}
            className="rounded-lg border border-black/10 px-3 py-1 dark:border-white/10"
          >
            Try again
          </button>
        </div>
      );
    }
    return <RankingTable entries={entries ?? []} />;
  }

  const data = current?.status === "ready" ? current.data : null;

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
        <section className={BOX_CLASS}>
          <h2 className="text-lg font-semibold">Top Men — Q-points</h2>
          {body(data?.men)}
        </section>
        <section className={BOX_CLASS}>
          <h2 className="text-lg font-semibold">Top Women — Q-points</h2>
          {body(data?.women)}
        </section>
      </div>
      <p className="mt-3 text-xs text-black/50 dark:text-white/50">
        Each athlete&apos;s best Q-points result{period === "year" ? " in the past year" : ""}. No age adjustment.
      </p>
    </div>
  );
}

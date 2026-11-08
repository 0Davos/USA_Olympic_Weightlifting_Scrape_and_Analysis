"use client";

import Link from "next/link";
import { useState } from "react";
import { BAR_CLASS, BOX_CLASS, ErrorOverlay, MUTED_CLASS, ROWS, useLoad } from "./QPointsLists";
import { fetchImprovers, type ImproverEntry, type Improvers } from "@/lib/rankings";

// The home page's bottom section: each gender's top 10 by Q-points gained over the past year (see
// compute_improvers in app/api/_rankings.py). No period toggle, so the loader's "period" is a constant.
const load = (_: "year", signal: AbortSignal) => fetchImprovers(signal);

// Always ROWS rows tall, with placeholder rows while loading, like the Q-points tables above.
function ImproverTable({ entries }: { entries: ImproverEntry[] | null }) {
  return (
    <table className="mt-3 w-full table-fixed text-sm">
      <thead className="text-left text-xs text-black/50 dark:text-white/50">
        <tr>
          <th className="w-7 pb-2 font-normal">#</th>
          <th className="pb-2 font-normal">Athlete</th>
          <th className="w-14 pb-2 text-right font-normal">Before</th>
          <th className="w-14 pb-2 text-right font-normal">Now</th>
          <th className="w-14 pb-2 text-right font-normal">Gain</th>
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
                  <div className="truncate text-xs text-black/50 dark:text-white/50" title={e.meet}>
                    {e.meet}
                  </div>
                </td>
                <td className="py-1.5 text-right tabular-nums text-black/60 dark:text-white/60">{e.before_q_points.toFixed(1)}</td>
                <td className="py-1.5 text-right tabular-nums">{e.q_points.toFixed(1)}</td>
                <td className="py-1.5 text-right font-medium tabular-nums">+{e.gain.toFixed(1)}</td>
              </tr>
            ))
          : Array.from({ length: ROWS }, (_, i) => (
              <tr key={i} className="border-t border-black/5 dark:border-white/5" aria-hidden>
                <td className="py-1.5 text-black/30 dark:text-white/30">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  <div className="flex h-5 items-center"><span className={`${BAR_CLASS} h-3.5 w-2/3`} /></div>
                  <div className="flex h-4 items-center"><span className={`${BAR_CLASS} h-2.5 w-1/2`} /></div>
                </td>
                <td className="py-1.5 text-right"><span className={`${BAR_CLASS} h-3.5 w-9 align-middle`} /></td>
                <td className="py-1.5 text-right"><span className={`${BAR_CLASS} h-3.5 w-9 align-middle`} /></td>
                <td className="py-1.5 text-right"><span className={`${BAR_CLASS} h-3.5 w-9 align-middle`} /></td>
              </tr>
            ))}
      </tbody>
    </table>
  );
}

export default function FastestImprovers() {
  const [attempt, setAttempt] = useState(0);
  const improvers = useLoad<Improvers, "year">(load, "year", attempt);
  const lists = improvers?.status === "ready" ? improvers.data : null;

  return (
    <div className="mt-10">
      <div className="grid gap-6 sm:grid-cols-2">
        {(["men", "women"] as const).map((g) => (
          <section key={g} className={`relative ${BOX_CLASS}`}>
            <h2 className="text-lg font-semibold">Fastest improvers — {g === "men" ? "Men" : "Women"}</h2>
            <div className={improvers?.status === "error" ? "invisible" : ""}>
              <ImproverTable entries={lists ? lists[g] : null} />
              {lists && lists[g].length === 0 && <p className={`mt-3 ${MUTED_CLASS}`}>No results in this period.</p>}
            </div>
            {improvers?.status === "error" && <ErrorOverlay what="improvers" onRetry={() => setAttempt((a) => a + 1)} />}
          </section>
        ))}
      </div>
      <p className="mt-3 text-xs text-black/50 dark:text-white/50">
        Q-points at each athlete&apos;s latest meet (within the past 12 months) compared with their best at any
        earlier meet, for athletes with at least 3 meets who also competed in the 12 months before it. No age
        adjustment.
      </p>
    </div>
  );
}

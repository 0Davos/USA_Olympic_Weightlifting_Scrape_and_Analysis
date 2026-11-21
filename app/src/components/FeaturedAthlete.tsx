"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchHistory, type Meet } from "@/lib/athlete";
import { BAR_CLASS, BOX_CLASS, MUTED_CLASS } from "./QPointsLists";

// The athlete shown in the home page's "Try it" box (chosen by the user 2026-11-21).
const FEATURED_ATHLETE = "Olivia Reeves";

type State = { status: "loading" } | { status: "ready"; name: string; meet: Meet } | { status: "error" };

// The athlete's most recent dated meet with a real total (bomb-outs skipped). Results come oldest first,
// with undated meets last.
function latestRealMeet(results: Meet[]): Meet | null {
  for (let i = results.length - 1; i >= 0; i--) {
    const r = results[i];
    if (r.date && !r.bombed_out && r.total != null && r.total > 0) return r;
  }
  return null;
}

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const kg = (v: number | null) => (v == null ? "—" : `${v} kg`);

// "Try it": a summary of one well-known athlete's latest meet and a link to her page, so a first-time
// visitor can see an athlete page (and its prediction) in one click.
export default function FeaturedAthlete() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchHistory(FEATURED_ATHLETE, controller.signal)
      .then((h) => {
        const meet = h && latestRealMeet(h.results);
        setState(h && meet ? { status: "ready", name: h.name, meet } : { status: "error" });
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setState({ status: "error" });
      });
    return () => controller.abort();
  }, []);

  const meet = state.status === "ready" ? state.meet : null;
  const stats: [string, string][] = [
    ["Snatch", kg(meet?.best_sn ?? null)],
    ["Clean & jerk", kg(meet?.best_cj ?? null)],
    ["Total", kg(meet?.total ?? null)],
    ["Bodyweight", kg(meet?.bodyweight ?? null)],
  ];

  return (
    <section className={`mt-6 ${BOX_CLASS}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-black/50 dark:text-white/50">Try it</p>
      <h2 className="mt-1 text-xl font-semibold">{state.status === "ready" ? state.name : FEATURED_ATHLETE}</h2>

      {state.status === "error" ? (
        <p className={`mt-3 ${MUTED_CLASS}`}>Couldn&apos;t load her latest meet right now.</p>
      ) : (
        <>
          <p className={`mt-1 ${MUTED_CLASS}`}>
            {meet ? (
              <>
                Most recent meet: {meet.meet}, {formatDate(meet.date!)}
              </>
            ) : (
              <span className={`${BAR_CLASS} h-3.5 w-64 align-middle`} aria-hidden />
            )}
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {stats.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-black/50 dark:text-white/50">{label}</dt>
                <dd className="mt-1 text-2xl font-semibold tabular-nums">
                  {meet ? value : <span className={`${BAR_CLASS} h-6 w-20 align-middle`} aria-hidden />}
                </dd>
              </div>
            ))}
          </dl>
        </>
      )}

      <p className={`mt-5 ${MUTED_CLASS}`}>
        Open her page and tick &ldquo;Predict future?&rdquo; to see where her next total is likely to land.
      </p>
      <Link
        href={`/athlete/${encodeURIComponent(FEATURED_ATHLETE)}`}
        className="mt-3 inline-block rounded-lg bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
      >
        View athlete
      </Link>
    </section>
  );
}

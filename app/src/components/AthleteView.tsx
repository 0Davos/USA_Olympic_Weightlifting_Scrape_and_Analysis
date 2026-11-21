"use client";

import { useEffect, useMemo, useState } from "react";
import { ATHLETE_STYLES, compareUrl, fetchHistory, type AthleteHistory } from "@/lib/athlete";
import AthleteGraph from "./AthleteGraph";
import ResultsTable from "./ResultsTable";

// The outcome of one fetch, tagged with the request it answers (athlete + retry count). Only
// an outcome matching the current request is used, so switching athletes can never show the
// previous athlete's data, and "loading" is simply "no outcome for this request yet".
type Load =
  | { key: string; status: "ready"; data: AthleteHistory }
  | { key: string; status: "notfound" }
  | { key: string; status: "error" };

const PLACEHOLDER_CLASS =
  "flex h-80 items-center justify-center rounded-xl border border-black/10 text-sm text-black/50 dark:border-white/10 dark:text-white/50";

export default function AthleteView({ name }: { name: string }) {
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<Load | null>(null);

  const key = `${name}#${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchHistory(name, controller.signal)
      .then((data) => setLoad(data ? { key, status: "ready", data } : { key, status: "notfound" }))
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoad({ key, status: "error" });
      });
    return () => controller.abort();
  }, [name, key]);

  const current = load && load.key === key ? load : null;
  const history = current?.status === "ready" ? current.data : null;
  // The whole history: the athlete page no longer has a date range filter (removed 2026-11-08).
  const rows = useMemo(() => history?.results ?? [], [history]);

  if (!current) return <div className={`mt-6 ${PLACEHOLDER_CLASS}`}>Loading results...</div>;

  if (current.status === "notfound") {
    return (
      <p className={`mt-6 ${PLACEHOLDER_CLASS}`}>
        No athlete found named &ldquo;{name}&rdquo;. Try the search box above.
      </p>
    );
  }

  if (current.status === "error" || !history) {
    return (
      <div className={`mt-6 flex-col gap-3 ${PLACEHOLDER_CLASS}`}>
        <p>Couldn&apos;t load results right now.</p>
        <button
          type="button"
          onClick={() => setAttempt((a) => a + 1)}
          className="rounded-lg border border-black/10 px-3 py-1.5 dark:border-white/10"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="mt-6">
        <AthleteGraph
          athletes={[
            { id: history.name, name: history.name, style: ATHLETE_STYLES[0], history, status: "ready", removable: false },
          ]}
          compareHref={compareUrl([history.name])}
        />
      </div>

      <div className="mt-10">
        <ResultsTable rows={rows} />
      </div>
    </>
  );
}

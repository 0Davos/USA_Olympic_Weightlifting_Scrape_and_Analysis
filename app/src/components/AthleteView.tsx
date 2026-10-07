"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchHistory, filterByDateRange, type AthleteHistory, type Metric } from "@/lib/athlete";
import GraphControls from "./GraphControls";
import Graph from "./Graph";
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
  const [metric, setMetric] = useState<Metric>("Total");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

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
  const rows = useMemo(
    () => (current?.status === "ready" ? filterByDateRange(current.data.results, from, to) : []),
    [current, from, to],
  );

  if (!current) return <div className={`mt-6 ${PLACEHOLDER_CLASS}`}>Loading results...</div>;

  if (current.status === "notfound") {
    return (
      <p className={`mt-6 ${PLACEHOLDER_CLASS}`}>
        No athlete found named &ldquo;{name}&rdquo;. Try the search box above.
      </p>
    );
  }

  if (current.status === "error") {
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
      <div className="mt-6 flex flex-col gap-4">
        <GraphControls
          metric={metric}
          onMetricChange={setMetric}
          from={from}
          to={to}
          onFromChange={setFrom}
          onToChange={setTo}
        />
        <Graph rows={rows} metric={metric} />
      </div>

      <div className="mt-10">
        <ResultsTable rows={rows} />
      </div>
    </>
  );
}

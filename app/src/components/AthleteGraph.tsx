"use client";

import { useEffect, useRef, useState } from "react";
import {
  addDays,
  fetchPrediction,
  lastBodyweight,
  MAX_PREDICT_DAYS_AHEAD,
  todayISO,
  type AthleteHistory,
  type AthleteStyle,
  type GraphPrediction,
  type GraphSeries,
  type Metric,
  type PredictionResult,
} from "@/lib/athlete";
import GraphControls, { type AthleteColumn } from "./GraphControls";
import Graph from "./Graph";

// One athlete on the graph. The athlete page passes one; the Compare page up to three.
export type GraphAthlete = {
  id: string; // stable while they're on the graph: keys their prediction date
  name: string;
  href?: string; // link to their page (Compare page)
  style: AthleteStyle;
  history: AthleteHistory | null; // null while loading, not found or failed
  status: AthleteColumn["status"];
  removable: boolean;
};

// One prediction request: exactly what was asked, so an answer for an old date is never shown against a
// new one.
type PredictionRequest = { key: string; name: string; date: string; bodyweight: number };

const DEFAULT_PREDICT_DAYS_AHEAD = 90; // the median gap between an athlete's meets is ~100 days
const PREDICT_DEBOUNCE_MS = 400;

// The lift choice, the per-athlete prediction controls and the graph, shared by the athlete page and the
// Compare page.
export default function AthleteGraph({
  athletes,
  compareHref,
  onRemove,
  onRetry,
}: {
  athletes: GraphAthlete[];
  compareHref?: string;
  onRemove?: (id: string) => void;
  onRetry?: (id: string) => void;
}) {
  const [metric, setMetric] = useState<Metric>("Total");

  // Predictions: one per athlete on the graph, each with its own date (the athlete's last bodyweight is
  // used automatically). Dates the user hasn't touched use the default (see below).
  const [predictOn, setPredictOn] = useState(false);
  const [targetDates, setTargetDates] = useState<Record<string, string>>({});
  const [outcomes, setOutcomes] = useState<Record<string, PredictionResult>>({});
  const outcomesRef = useRef(outcomes);
  useEffect(() => {
    outcomesRef.current = outcomes;
  }, [outcomes]);

  const [today] = useState(todayISO); // fixed at mount; the API enforces the real limit anyway
  const maxDate = addDays(today, MAX_PREDICT_DAYS_AHEAD);
  // Only the Total graph has predictions (the models predict Total).
  const predictAvailable = metric === "Total";

  // Everything a prediction needs, per athlete.
  const plans = athletes.map((e) => {
    const results = e.history?.results ?? [];
    const latest = [...results].reverse().find((r) => r.date) ?? null; // the bands start from it
    const lastRealTotal = [...results].reverse().find((r) => r.date && !r.bombed_out)?.total ?? null;
    const minDate = latest?.date ? addDays(latest.date, 1) : "";
    // Default: about three months after the later of today and their latest meet.
    const base = latest?.date && latest.date > today ? latest.date : today;
    const wanted = addDays(base, DEFAULT_PREDICT_DAYS_AHEAD);
    const date = targetDates[e.id] ?? (wanted > maxDate ? maxDate : wanted);
    const dateValid = /^\d{4}-\d{2}-\d{2}$/.test(date) && date >= minDate && date <= maxDate;
    const bodyweight = lastBodyweight(results);
    const request: PredictionRequest | null =
      e.history && latest && predictOn && predictAvailable && dateValid && bodyweight != null
        ? { key: `${e.history.name}|${date}|${bodyweight}`, name: e.history.name, date, bodyweight }
        : null;
    return { entry: e, latest, lastRealTotal, minDate, date, dateValid, bodyweight, request };
  });

  // Ask for each athlete's prediction once their inputs are valid and typing pauses. Answers are kept by
  // request, so changing one athlete's date never refetches another's.
  const requests = plans.flatMap((p) => (p.request ? [p.request] : []));
  const requestsKey = requests.map((r) => r.key).join("\n");
  useEffect(() => {
    const missing = requests.filter((r) => !(r.key in outcomesRef.current));
    if (missing.length === 0) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      for (const r of missing) {
        fetchPrediction(r.name, r.date, r.bodyweight, controller.signal)
          .then((result) => setOutcomes((m) => ({ ...m, [r.key]: result })))
          .catch((err) => {
            if (err instanceof DOMException && err.name === "AbortError") return;
            setOutcomes((m) => ({ ...m, [r.key]: { ok: false, message: "Prediction is unavailable right now." } }));
          });
      }
    }, PREDICT_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // requestsKey stands for `requests` (a new array every render)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestsKey]);

  // ---- what the controls and the graph show
  const columns: AthleteColumn[] = plans.map((p) => {
    const e = p.entry;
    const answered = p.request ? (outcomes[p.request.key] ?? null) : null;
    let message: AthleteColumn["message"] = null;
    if (predictOn && predictAvailable && e.history) {
      if (p.bodyweight == null) message = { tone: "error", text: "No bodyweight on record to predict from." };
      else if (!p.dateValid) message = { tone: "error", text: `Pick a date between ${p.minDate} and ${maxDate}.` };
      else if (answered && !answered.ok) message = { tone: "error", text: answered.message };
      // (Only problems are shown under the date; that predictions use the last bodyweight is a note at the
      // bottom of the page.)
    }
    return {
      id: e.id,
      name: e.name,
      href: e.href,
      color: e.style.color,
      shape: e.style.shape,
      removable: e.removable,
      status: e.status,
      date: p.date,
      minDate: p.minDate,
      dateEnabled: predictOn && predictAvailable && e.history != null,
      message,
    };
  });

  const series: GraphSeries[] = plans.flatMap((p) =>
    p.entry.history ? [{ name: p.entry.name, rows: p.entry.history.results, ...p.entry.style }] : [],
  );

  const predictions: GraphPrediction[] = predictAvailable
    ? plans.flatMap((p) => {
        const answered = p.request ? outcomes[p.request.key] : undefined;
        if (!answered?.ok) return [];
        const latestMeet = answered.data.latest_meet;
        const originTotal = latestMeet.bombed_out ? p.lastRealTotal : latestMeet.total;
        return originTotal == null ? [] : [{ name: p.entry.name, prediction: answered.data, originTotal, ...p.entry.style }];
      })
    : [];

  return (
    <div className="flex flex-col gap-4">
      <GraphControls
        metric={metric}
        onMetricChange={setMetric}
        predictOn={predictOn}
        onPredictToggle={setPredictOn}
        predictAvailable={predictAvailable}
        maxDate={maxDate}
        athletes={columns}
        onDateChange={(id, date) => setTargetDates((d) => ({ ...d, [id]: date }))}
        compareHref={compareHref}
        onRemove={onRemove}
        onRetry={onRetry}
      />
      <Graph series={series} metric={metric} predictions={predictions} />
    </div>
  );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  addDays,
  ATHLETE_STYLES,
  fetchHistory,
  fetchPrediction,
  filterByDateRange,
  lastBodyweight,
  MAX_COMPARED,
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
import ResultsTable from "./ResultsTable";

// The outcome of one fetch, tagged with the request it answers (athlete + retry count). Only
// an outcome matching the current request is used, so switching athletes can never show the
// previous athlete's data, and "loading" is simply "no outcome for this request yet".
type Load =
  | { key: string; status: "ready"; data: AthleteHistory }
  | { key: string; status: "notfound" }
  | { key: string; status: "error" };

// A compared athlete's history, by the name that was picked.
type CompareLoad = { status: "ready"; data: AthleteHistory } | { status: "notfound" } | { status: "error" };

// One prediction request: exactly what was asked, so an answer for an old date is never shown against a
// new one.
type PredictionRequest = { key: string; name: string; date: string; bodyweight: number };

// The same key the API matches names on (trimmed, whitespace collapsed, lowercased).
function nameKey(name: string) {
  return name.replace(/\s+/g, " ").trim().toLowerCase();
}

const PLACEHOLDER_CLASS =
  "flex h-80 items-center justify-center rounded-xl border border-black/10 text-sm text-black/50 dark:border-white/10 dark:text-white/50";

const DEFAULT_PREDICT_DAYS_AHEAD = 90; // the median gap between an athlete's meets is ~100 days
const PREDICT_DEBOUNCE_MS = 400;
const MAIN_ID = "\u0000main"; // the page's own athlete, in maps keyed by picked name

export default function AthleteView({ name }: { name: string }) {
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<Load | null>(null);
  const [metric, setMetric] = useState<Metric>("Total");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  // Predictions: one per athlete on the graph, each with its own date (the athlete's last bodyweight is
  // used automatically). Dates the user hasn't touched use the default (see defaultDate).
  const [predictOn, setPredictOn] = useState(false);
  const [targetDates, setTargetDates] = useState<Record<string, string>>({});
  const [outcomes, setOutcomes] = useState<Record<string, PredictionResult>>({});
  const outcomesRef = useRef(outcomes);
  useEffect(() => {
    outcomesRef.current = outcomes;
  }, [outcomes]);

  // Compare: other athletes overlaid on the graph, in the order they were added.
  const [compareNames, setCompareNames] = useState<string[]>([]);
  // Each compared athlete keeps the colour/shape slot (1..MAX_COMPARED in ATHLETE_STYLES) they got when
  // added, so removing one never repaints the other.
  const [compareSlots, setCompareSlots] = useState<Record<string, number>>({});
  const [compareLoads, setCompareLoads] = useState<Record<string, CompareLoad>>({});
  const [compareRetry, setCompareRetry] = useState(0);
  const compareLoadsRef = useRef(compareLoads);
  useEffect(() => {
    compareLoadsRef.current = compareLoads;
  }, [compareLoads]);

  // Fetch each compared athlete's history once (again after a retry). Reading the loads through a ref
  // keeps one athlete's answer from cancelling another's request still in flight.
  useEffect(() => {
    const missing = compareNames.filter((n) => !(n in compareLoadsRef.current));
    if (missing.length === 0) return;
    const controller = new AbortController();
    for (const n of missing) {
      fetchHistory(n, controller.signal)
        .then((data) => setCompareLoads((m) => ({ ...m, [n]: data ? { status: "ready", data } : { status: "notfound" } })))
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setCompareLoads((m) => ({ ...m, [n]: { status: "error" } }));
        });
    }
    return () => controller.abort();
  }, [compareNames, compareRetry]);

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
  const rows = useMemo(
    () => (history ? filterByDateRange(history.results, from, to) : []),
    [history, from, to],
  );

  const [today] = useState(todayISO); // fixed at mount; the API enforces the real limit anyway
  const maxDate = addDays(today, MAX_PREDICT_DAYS_AHEAD);
  // Only the Total graph has predictions (the models predict Total).
  const predictAvailable = metric === "Total";

  // ---- the athletes on the graph: the page's own, then the compared ones
  const styleOf = (n: string) => ATHLETE_STYLES[compareSlots[n] ?? 1];
  type Entry = { id: string; name: string; style: AthleteStyle; history: AthleteHistory | null; status: AthleteColumn["status"] };
  const entries: Entry[] = history
    ? [
        { id: MAIN_ID, name: history.name, style: ATHLETE_STYLES[0], history, status: "ready" },
        ...compareNames.map((n): Entry => {
          const l = compareLoads[n];
          return {
            id: n,
            name: l?.status === "ready" ? l.data.name : n,
            style: styleOf(n),
            history: l?.status === "ready" ? l.data : null,
            status: l ? l.status : "loading",
          };
        }),
      ]
    : [];

  // Everything a prediction needs, per athlete.
  const plans = entries.map((e) => {
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
        ? { key: `${e.name}|${date}|${bodyweight}`, name: e.name, date, bodyweight }
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

  // ---- compare
  function addCompare(picked: string) {
    const k = nameKey(picked);
    if (k === nameKey(history?.name ?? name)) return; // already the page's athlete
    if (compareNames.some((n) => nameKey(n) === k) || compareNames.length >= MAX_COMPARED) return;
    const taken = new Set(Object.values(compareSlots));
    const slot = Array.from({ length: MAX_COMPARED }, (_, i) => i + 1).find((s) => !taken.has(s)) ?? 1;
    setCompareNames([...compareNames, picked]);
    setCompareSlots({ ...compareSlots, [picked]: slot });
  }
  function removeCompare(picked: string) {
    setCompareNames((names) => names.filter((n) => n !== picked));
    setCompareSlots((slots) => {
      const rest = { ...slots };
      delete rest[picked];
      return rest;
    });
  }
  function retryCompare(picked: string) {
    setCompareLoads((m) => {
      const rest = { ...m };
      delete rest[picked];
      compareLoadsRef.current = rest; // so the effect sees it as missing straight away
      return rest;
    });
    setCompareRetry((r) => r + 1);
  }

  // ---- what the controls and the graph show
  const columns: AthleteColumn[] = plans.map((p) => {
    const e = p.entry;
    const answered = p.request ? (outcomes[p.request.key] ?? null) : null;
    let message: AthleteColumn["message"] = null;
    if (predictOn && predictAvailable && e.history) {
      if (p.bodyweight == null) message = { tone: "error", text: "No bodyweight on record to predict from." };
      else if (!p.dateValid) message = { tone: "error", text: `Pick a date between ${p.minDate} and ${maxDate}.` };
      else if (!answered) message = { tone: "info", text: "Predicting..." };
      else if (!answered.ok) message = { tone: "error", text: answered.message };
      else {
        const n = answered.data.meets_used;
        message = { tone: "info", text: `From ${n} meet${n === 1 ? "" : "s"}, at their last bodyweight (${p.bodyweight} kg).` };
      }
    }
    return {
      id: e.id,
      name: e.name,
      color: e.style.color,
      shape: e.style.shape,
      removable: e.id !== MAIN_ID,
      status: e.status,
      date: p.date,
      minDate: p.minDate,
      dateEnabled: predictOn && predictAvailable && e.history != null,
      message,
    };
  });

  const series: GraphSeries[] = plans.flatMap((p) =>
    p.entry.history
      ? [{ name: p.entry.name, rows: p.entry.id === MAIN_ID ? rows : filterByDateRange(p.entry.history.results, from, to), ...p.entry.style }]
      : [],
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
          predictOn={predictOn}
          onPredictToggle={setPredictOn}
          predictAvailable={predictAvailable}
          maxDate={maxDate}
          athletes={columns}
          onDateChange={(id, date) => setTargetDates((d) => ({ ...d, [id]: date }))}
          canCompare={compareNames.length < MAX_COMPARED}
          onCompareAdd={addCompare}
          onCompareRemove={removeCompare}
          onCompareRetry={retryCompare}
        />
        <Graph series={series} metric={metric} predictions={predictions} />
      </div>

      <div className="mt-10">
        <ResultsTable rows={rows} />
      </div>
    </>
  );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  addDays,
  ATHLETE_STYLES,
  fetchHistory,
  fetchPrediction,
  filterByDateRange,
  MAX_BODYWEIGHT,
  MAX_COMPARED,
  MAX_PREDICT_DAYS_AHEAD,
  MIN_BODYWEIGHT,
  todayISO,
  type AthleteHistory,
  type GraphSeries,
  type Metric,
  type PredictionResult,
} from "@/lib/athlete";
import GraphControls, { type ComparedChip, type PredictionMessage } from "./GraphControls";
import Graph from "./Graph";
import ResultsTable from "./ResultsTable";

// The outcome of one fetch, tagged with the request it answers (athlete + retry count). Only
// an outcome matching the current request is used, so switching athletes can never show the
// previous athlete's data, and "loading" is simply "no outcome for this request yet".
type Load =
  | { key: string; status: "ready"; data: AthleteHistory }
  | { key: string; status: "notfound" }
  | { key: string; status: "error" };

// Same idea for predictions: keyed by exactly what was asked, so an answer for an old date or
// bodyweight is never shown against new inputs.
type PredictionOutcome = { key: string; result: PredictionResult };

// A compared athlete's history, by the name that was picked.
type CompareLoad = { status: "ready"; data: AthleteHistory } | { status: "notfound" } | { status: "error" };

// The same key the API matches names on (trimmed, whitespace collapsed, lowercased).
function nameKey(name: string) {
  return name.replace(/\s+/g, " ").trim().toLowerCase();
}

const PLACEHOLDER_CLASS =
  "flex h-80 items-center justify-center rounded-xl border border-black/10 text-sm text-black/50 dark:border-white/10 dark:text-white/50";

const DEFAULT_PREDICT_DAYS_AHEAD = 90; // the median gap between an athlete's meets is ~100 days
const PREDICT_DEBOUNCE_MS = 400;

export default function AthleteView({ name }: { name: string }) {
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<Load | null>(null);
  const [metric, setMetric] = useState<Metric>("Total");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const [predictOn, setPredictOn] = useState(false);
  const [targetDate, setTargetDate] = useState("");
  const [bodyweight, setBodyweight] = useState("");
  const [outcome, setOutcome] = useState<PredictionOutcome | null>(null);

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

  // ---- prediction inputs
  // The athlete's latest dated meet: the predicted meet must come after it, and the bands start from it.
  const latest = history ? ([...history.results].reverse().find((r) => r.date) ?? null) : null;
  const lastRealTotal = history ? ([...history.results].reverse().find((r) => r.date && !r.bombed_out)?.total ?? null) : null;
  const [today] = useState(todayISO); // fixed at mount; the API enforces the real limit anyway
  const minDate = latest?.date ? addDays(latest.date, 1) : "";
  const maxDate = addDays(today, MAX_PREDICT_DAYS_AHEAD);

  const bodyweightNum = Number(bodyweight);
  const dateValid = /^\d{4}-\d{2}-\d{2}$/.test(targetDate) && targetDate >= minDate && targetDate <= maxDate;
  const bodyweightValid = bodyweight !== "" && bodyweightNum >= MIN_BODYWEIGHT && bodyweightNum <= MAX_BODYWEIGHT;
  // Only the Total graph has predictions (the models predict Total).
  const predictAvailable = metric === "Total";
  const predictionKey =
    history && latest && predictOn && predictAvailable && dateValid && bodyweightValid
      ? `${name}|${targetDate}|${bodyweightNum}`
      : null;

  // Ask for a prediction once the inputs are valid and typing pauses; cancel the previous request
  // if they change again. The first request on a cold server is also what warms it up.
  useEffect(() => {
    if (!predictionKey) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetchPrediction(name, targetDate, bodyweightNum, controller.signal)
        .then((result) => setOutcome({ key: predictionKey, result }))
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setOutcome({ key: predictionKey, result: { ok: false, message: "Prediction is unavailable right now." } });
        });
    }, PREDICT_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [predictionKey, name, targetDate, bodyweightNum]);

  const answered = predictionKey && outcome?.key === predictionKey ? outcome.result : null;
  const prediction = answered?.ok ? answered.data : null;

  function onPredictToggle(on: boolean) {
    setPredictOn(on);
    if (!on) return;
    // Pre-fill sensible values so ticking the box shows something straight away: a meet about three
    // months after the later of today and the athlete's latest meet, at their last recorded bodyweight.
    if (!targetDate && latest?.date) {
      const base = latest.date > todayISO() ? latest.date : todayISO();
      const wanted = addDays(base, DEFAULT_PREDICT_DAYS_AHEAD);
      setTargetDate(wanted > maxDate ? maxDate : wanted);
    }
    if (!bodyweight && latest?.bodyweight != null) setBodyweight(String(latest.bodyweight));
  }

  let message: PredictionMessage | null = null;
  if (predictOn && predictAvailable) {
    if (!dateValid) {
      message = { tone: "error", text: `Pick a date between ${minDate} and ${maxDate}.` };
    } else if (!bodyweightValid) {
      message = { tone: "error", text: `Enter a bodyweight between ${MIN_BODYWEIGHT} and ${MAX_BODYWEIGHT} kg.` };
    } else if (!answered) {
      message = { tone: "info", text: "Predicting..." };
    } else if (!answered.ok) {
      message = { tone: "error", text: answered.message };
    } else {
      // The one place the prediction is described (the no-bomb-out note is in the controls' helper
      // text just above); the bands' values are on the graph's hover.
      const { date, bodyweight, meets_used } = answered.data;
      // While comparing, say whose prediction it is: only the page's own athlete gets one.
      const whose = compareNames.length > 0 && history ? `${history.name}: ` : "";
      message = {
        tone: "info",
        text: `${whose}Predicted total for ${date} at ${bodyweight} kg, from ${meets_used} meet${meets_used === 1 ? "" : "s"}.`,
      };
    }
  }

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

  const styleOf = (n: string) => ATHLETE_STYLES[compareSlots[n] ?? 1];
  const comparedChips: ComparedChip[] = compareNames.map((n) => {
    const l = compareLoads[n];
    return {
      name: l?.status === "ready" ? l.data.name : n,
      ...styleOf(n),
      status: l ? l.status : "loading",
    };
  });
  // Keep the chip's remove/retry pointed at the name that was picked (the display name can differ).
  const chipActions = Object.fromEntries(comparedChips.map((c, i) => [c.name, compareNames[i]]));

  const series: GraphSeries[] = history
    ? [
        { name: history.name, rows, ...ATHLETE_STYLES[0] },
        ...compareNames.flatMap((n) => {
          const l = compareLoads[n];
          return l?.status === "ready"
            ? [{ name: l.data.name, rows: filterByDateRange(l.data.results, from, to), ...styleOf(n) }]
            : [];
        }),
      ]
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
          onPredictToggle={onPredictToggle}
          predictAvailable={predictAvailable}
          targetDate={targetDate}
          onTargetDateChange={setTargetDate}
          bodyweight={bodyweight}
          onBodyweightChange={setBodyweight}
          minDate={minDate}
          maxDate={maxDate}
          message={message}
          compared={comparedChips}
          onCompareAdd={addCompare}
          onCompareRemove={(shown) => removeCompare(chipActions[shown] ?? shown)}
          onCompareRetry={(shown) => retryCompare(chipActions[shown] ?? shown)}
        />
        <Graph
          series={series}
          metric={metric}
          prediction={predictAvailable ? prediction : null}
          originTotal={prediction ? (prediction.latest_meet.bombed_out ? lastRealTotal : prediction.latest_meet.total) : null}
        />
      </div>

      <div className="mt-10">
        <ResultsTable rows={rows} />
      </div>
    </>
  );
}

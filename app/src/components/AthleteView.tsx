"use client";

import { useEffect, useMemo, useState } from "react";
import {
  addDays,
  fetchHistory,
  fetchPrediction,
  filterByDateRange,
  MAX_BODYWEIGHT,
  MAX_PREDICT_DAYS_AHEAD,
  MIN_BODYWEIGHT,
  todayISO,
  type AthleteHistory,
  type Metric,
  type PredictionResult,
} from "@/lib/athlete";
import GraphControls, { type PredictionMessage } from "./GraphControls";
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
      const p = answered.data.prediction;
      message = {
        tone: "info",
        text: `Predicted total on ${answered.data.date} at ${answered.data.bodyweight} kg: ${p.q50} kg (likely ${p.q25}–${p.q75} kg, 99% chance under ${p.q99} kg).`,
      };
    }
  }

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
        />
        <Graph
          rows={rows}
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

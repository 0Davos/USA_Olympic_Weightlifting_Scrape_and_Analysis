"use client";

import { METRICS, MIN_BODYWEIGHT, MAX_BODYWEIGHT, type Metric } from "@/lib/athlete";

export type PredictionMessage = { tone: "info" | "error"; text: string };

type Props = {
  metric: Metric;
  onMetricChange: (metric: Metric) => void;
  from: string;
  to: string;
  onFromChange: (from: string) => void;
  onToChange: (to: string) => void;
  // Prediction row. The inputs' state lives in AthleteView, which also does the fetching.
  predictOn: boolean;
  onPredictToggle: (on: boolean) => void;
  predictAvailable: boolean; // false on the Sn and Cj views: the models only predict Total
  targetDate: string;
  onTargetDateChange: (date: string) => void;
  bodyweight: string;
  onBodyweightChange: (bodyweight: string) => void;
  minDate: string; // the day after the athlete's latest meet
  maxDate: string; // 12 months from today
  message: PredictionMessage | null;
};

const INPUT_CLASS =
  "rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm dark:border-white/10";

export default function GraphControls({
  metric,
  onMetricChange,
  from,
  to,
  onFromChange,
  onToChange,
  predictOn,
  onPredictToggle,
  predictAvailable,
  targetDate,
  onTargetDateChange,
  bodyweight,
  onBodyweightChange,
  minDate,
  maxDate,
  message,
}: Props) {
  const inputsDisabled = !predictOn || !predictAvailable;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <select
            aria-label="Lift to graph"
            value={metric}
            onChange={(e) => onMetricChange(e.target.value as Metric)}
            className="rounded-lg border border-black/10 bg-white px-3 py-1.5 text-sm text-black dark:border-white/10 dark:bg-black dark:text-white"
          >
            {METRICS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-sm">
            From
            <input type="date" value={from} max={to || undefined} onChange={(e) => onFromChange(e.target.value)} className={INPUT_CLASS} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            To
            <input type="date" value={to} min={from || undefined} onChange={(e) => onToChange(e.target.value)} className={INPUT_CLASS} />
          </label>
          {(from || to) && (
            <button
              type="button"
              onClick={() => {
                onFromChange("");
                onToChange("");
              }}
              className="text-sm underline text-black/60 dark:text-white/60"
            >
              Clear dates
            </button>
          )}
        </div>

        <button
          type="button"
          disabled
          className="cursor-not-allowed rounded-lg border border-black/10 px-3 py-1.5 text-sm text-black/40 dark:border-white/10 dark:text-white/40"
        >
          Compare
        </button>
      </div>

      <div className="flex flex-col gap-2 border-t border-black/10 pt-3 dark:border-white/10">
        <div className="flex flex-wrap items-center gap-4">
          <label className={`flex items-center gap-2 text-sm ${predictAvailable ? "" : "opacity-40"}`}>
            <input
              type="checkbox"
              checked={predictOn && predictAvailable}
              disabled={!predictAvailable}
              onChange={(e) => onPredictToggle(e.target.checked)}
            />
            Predict future?
          </label>

          <input
            type="date"
            aria-label="Date of the meet to predict"
            value={targetDate}
            min={minDate}
            max={maxDate}
            onChange={(e) => onTargetDateChange(e.target.value)}
            disabled={inputsDisabled}
            className={`${INPUT_CLASS} disabled:opacity-40`}
          />

          <input
            type="number"
            aria-label="Bodyweight at that meet (kg)"
            value={bodyweight}
            onChange={(e) => onBodyweightChange(e.target.value)}
            disabled={inputsDisabled}
            min={MIN_BODYWEIGHT}
            max={MAX_BODYWEIGHT}
            step={0.1}
            placeholder="Bodyweight (kg)"
            className={`${INPUT_CLASS} disabled:opacity-40`}
          />
        </div>

        {!predictAvailable && (
          <p className="text-xs text-black/50 dark:text-white/50">Predictions are available for Total only.</p>
        )}
        {predictOn && predictAvailable && (
          <p className="text-xs text-black/50 dark:text-white/50">
            Predictions go up to 12 months ahead (through {maxDate}) and assume no bomb-out.
          </p>
        )}
        {predictOn && predictAvailable && message && (
          <p className={`text-sm ${message.tone === "error" ? "text-red-600 dark:text-red-400" : ""}`}>{message.text}</p>
        )}
      </div>
    </div>
  );
}

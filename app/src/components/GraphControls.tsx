"use client";

import { useState } from "react";
import { METRICS, MIN_BODYWEIGHT, MAX_BODYWEIGHT, MAX_COMPARED, type MarkerShape, type Metric } from "@/lib/athlete";
import AthleteSearch from "./AthleteSearch";

export type PredictionMessage = { tone: "info" | "error"; text: string };

// A compared athlete as the controls show it: a chip in their colour and shape, with remove (and retry
// if their results failed to load).
export type ComparedChip = {
  name: string;
  color: string;
  shape: MarkerShape;
  status: "loading" | "ready" | "notfound" | "error";
};

function ChipMarker({ color, shape }: { color: string; shape: MarkerShape }) {
  const style = { backgroundColor: color };
  if (shape === "square") return <span className="inline-block h-2.5 w-2.5 rounded-[2px]" style={style} />;
  if (shape === "diamond") return <span className="inline-block h-2.5 w-2.5 rotate-45 rounded-[1px]" style={style} />;
  return <span className="inline-block h-2.5 w-2.5 rounded-full" style={style} />;
}

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
  // Compare: athletes overlaid on the graph (up to MAX_COMPARED).
  compared: ComparedChip[];
  onCompareAdd: (name: string) => void;
  onCompareRemove: (name: string) => void;
  onCompareRetry: (name: string) => void;
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
  compared,
  onCompareAdd,
  onCompareRemove,
  onCompareRetry,
}: Props) {
  const inputsDisabled = !predictOn || !predictAvailable;
  const [searching, setSearching] = useState(false);
  const canAdd = compared.length < MAX_COMPARED;

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
          onClick={() => setSearching((s) => !s)}
          disabled={!canAdd && !searching}
          aria-expanded={searching}
          title={canAdd ? "Add another athlete to the graph" : `Up to ${MAX_COMPARED} athletes can be compared`}
          className={`rounded-lg border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40 ${
            searching
              ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
              : "border-black/10 dark:border-white/10"
          }`}
        >
          Compare
        </button>
      </div>

      {(searching || compared.length > 0) && (
        <div className="flex flex-wrap items-center gap-2">
          {compared.map((c) => (
            <span
              key={c.name}
              className="flex items-center gap-1.5 rounded-full border border-black/10 py-1 pl-3 pr-1 text-sm dark:border-white/10"
            >
              <ChipMarker color={c.color} shape={c.shape} />
              {c.name}
              {c.status === "loading" && <span className="text-xs text-black/50 dark:text-white/50">loading…</span>}
              {c.status === "notfound" && <span className="text-xs text-red-600 dark:text-red-400">not found</span>}
              {c.status === "error" && (
                <button type="button" onClick={() => onCompareRetry(c.name)} className="text-xs text-red-600 underline dark:text-red-400">
                  couldn&apos;t load — retry
                </button>
              )}
              <button
                type="button"
                onClick={() => onCompareRemove(c.name)}
                aria-label={`Remove ${c.name} from the comparison`}
                className="flex h-5 w-5 items-center justify-center rounded-full text-black/50 hover:bg-black/5 hover:text-black dark:text-white/50 dark:hover:bg-white/10 dark:hover:text-white"
              >
                ×
              </button>
            </span>
          ))}
          {searching && canAdd && (
            <AthleteSearch
              idPrefix="compare"
              autoFocus
              placeholder="Add an athlete to compare..."
              className="w-full max-w-xs"
              onSelect={(name) => {
                onCompareAdd(name);
                setSearching(false);
              }}
              onEscape={() => setSearching(false)}
            />
          )}
        </div>
      )}

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

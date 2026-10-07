"use client";

import { useState } from "react";
import { METRICS, type Metric } from "@/lib/athlete";

type Props = {
  metric: Metric;
  onMetricChange: (metric: Metric) => void;
  from: string;
  to: string;
  onFromChange: (from: string) => void;
  onToChange: (to: string) => void;
};

const INPUT_CLASS =
  "rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm dark:border-white/10";

export default function GraphControls({ metric, onMetricChange, from, to, onFromChange, onToChange }: Props) {
  // Post-MVP (future prediction): these three are placeholders and not wired to anything yet.
  const [predictFuture, setPredictFuture] = useState(false);
  const [targetDate, setTargetDate] = useState("");
  const [bodyweight, setBodyweight] = useState("");

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

      <div className="flex flex-wrap items-center gap-4 border-t border-black/10 pt-3 dark:border-white/10">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={predictFuture}
            onChange={(e) => setPredictFuture(e.target.checked)}
          />
          Predict future?
        </label>

        <input
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
          disabled={!predictFuture}
          className={`${INPUT_CLASS} disabled:opacity-40`}
        />

        <input
          type="number"
          value={bodyweight}
          onChange={(e) => setBodyweight(e.target.value)}
          disabled={!predictFuture}
          min={0.1}
          max={299.9}
          step={0.1}
          placeholder="Bodyweight (kg)"
          className={`${INPUT_CLASS} disabled:opacity-40`}
        />
      </div>
    </div>
  );
}

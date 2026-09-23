"use client";

import { useState } from "react";

const METRICS = ["Sn", "Cj", "Total"] as const;

export default function GraphControls() {
  const [metric, setMetric] = useState<(typeof METRICS)[number]>("Total");
  const [predictFuture, setPredictFuture] = useState(false);
  const [targetDate, setTargetDate] = useState("");
  const [bodyweight, setBodyweight] = useState("");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value as (typeof METRICS)[number])}
          className="rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm text-black dark:border-white/10"
        >
          {METRICS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

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
          className="rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm disabled:opacity-40 dark:border-white/10"
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
          className="rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm disabled:opacity-40 dark:border-white/10"
        />
      </div>
    </div>
  );
}

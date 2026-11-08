"use client";

import { useState } from "react";
import { METRICS, type MarkerShape, type Metric } from "@/lib/athlete";
import AthleteSearch from "./AthleteSearch";

// One athlete on the graph as the controls show them: their name (with remove, for compared athletes)
// right above their own prediction date, and what their prediction is doing underneath.
export type AthleteColumn = {
  id: string; // what onDateChange / onCompareRemove / onCompareRetry get back
  name: string;
  color: string;
  shape: MarkerShape;
  removable: boolean; // false for the page's own athlete
  status: "loading" | "ready" | "notfound" | "error"; // their results
  date: string;
  minDate: string; // the day after their latest meet
  dateEnabled: boolean;
  message: { tone: "info" | "error"; text: string } | null;
};

type Props = {
  metric: Metric;
  onMetricChange: (metric: Metric) => void;
  predictOn: boolean;
  onPredictToggle: (on: boolean) => void;
  predictAvailable: boolean; // false on the Sn and Cj views: the models only predict Total
  maxDate: string; // 12 months from today
  athletes: AthleteColumn[]; // the page's athlete first
  onDateChange: (id: string, date: string) => void;
  canCompare: boolean;
  onCompareAdd: (name: string) => void;
  onCompareRemove: (id: string) => void;
  onCompareRetry: (id: string) => void;
};

const INPUT_CLASS =
  "rounded-lg border border-black/10 bg-transparent px-3 py-1.5 text-sm dark:border-white/10";

function ChipMarker({ color, shape }: { color: string; shape: MarkerShape }) {
  const style = { backgroundColor: color };
  if (shape === "square") return <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-[2px]" style={style} />;
  if (shape === "diamond") return <span className="inline-block h-2.5 w-2.5 shrink-0 rotate-45 rounded-[1px]" style={style} />;
  return <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full" style={style} />;
}

export default function GraphControls({
  metric,
  onMetricChange,
  predictOn,
  onPredictToggle,
  predictAvailable,
  maxDate,
  athletes,
  onDateChange,
  canCompare,
  onCompareAdd,
  onCompareRemove,
  onCompareRetry,
}: Props) {
  const [searching, setSearching] = useState(false);

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

        </div>

        <button
          type="button"
          onClick={() => setSearching((s) => !s)}
          disabled={!canCompare && !searching}
          aria-expanded={searching}
          title={canCompare ? "Add another athlete to the graph" : "Up to 3 athletes can be on the graph"}
          className={`rounded-lg border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40 ${
            searching
              ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
              : "border-black/10 dark:border-white/10"
          }`}
        >
          Compare
        </button>
      </div>

      {searching && canCompare && (
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

      <div className="flex flex-col gap-3 border-t border-black/10 pt-3 dark:border-white/10">
        <label className={`flex items-center gap-2 text-sm ${predictAvailable ? "" : "opacity-40"}`}>
          <input
            type="checkbox"
            checked={predictOn && predictAvailable}
            disabled={!predictAvailable}
            onChange={(e) => onPredictToggle(e.target.checked)}
          />
          Predict future?
        </label>

        {/* One column per athlete: name (and remove) right above their prediction date. */}
        <div className="flex flex-wrap gap-x-6 gap-y-4">
          {athletes.map((a) => (
            <div key={a.id} className="flex w-full max-w-[16rem] flex-col gap-1.5 sm:w-auto">
              <div className="flex min-h-7 items-center gap-1.5 text-sm">
                <ChipMarker color={a.color} shape={a.shape} />
                <span className="truncate font-medium" title={a.name}>{a.name}</span>
                {a.status === "loading" && <span className="text-xs text-black/50 dark:text-white/50">loading…</span>}
                {a.status === "notfound" && <span className="text-xs text-red-600 dark:text-red-400">not found</span>}
                {a.status === "error" && (
                  <button type="button" onClick={() => onCompareRetry(a.id)} className="text-xs text-red-600 underline dark:text-red-400">
                    couldn&apos;t load — retry
                  </button>
                )}
                {a.removable && (
                  <button
                    type="button"
                    onClick={() => onCompareRemove(a.id)}
                    aria-label={`Remove ${a.name} from the comparison`}
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-black/50 hover:bg-black/5 hover:text-black dark:text-white/50 dark:hover:bg-white/10 dark:hover:text-white"
                  >
                    ×
                  </button>
                )}
              </div>
              <input
                type="date"
                aria-label={`Date of ${a.name}'s meet to predict`}
                value={a.date}
                min={a.minDate || undefined}
                max={maxDate}
                onChange={(e) => onDateChange(a.id, e.target.value)}
                disabled={!a.dateEnabled}
                className={`${INPUT_CLASS} disabled:opacity-40`}
              />
              {a.message && (
                <p className={`text-xs ${a.message.tone === "error" ? "text-red-600 dark:text-red-400" : "text-black/60 dark:text-white/60"}`}>
                  {a.message.text}
                </p>
              )}
            </div>
          ))}
        </div>

        {!predictAvailable && (
          <p className="text-xs text-black/50 dark:text-white/50">Predictions are available for Total only.</p>
        )}
        {predictOn && predictAvailable && (
          <p className="text-xs text-black/50 dark:text-white/50">
            Predictions go up to 12 months ahead (through {maxDate}) and assume no bomb-out.
          </p>
        )}
      </div>
    </div>
  );
}

"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  useXAxisScale,
  useYAxisScale,
  XAxis,
  YAxis,
} from "recharts";
import { METRIC_FIELD, type Meet, type Metric, type Prediction } from "@/lib/athlete";

type Point = {
  kind: "meet";
  t: number;
  value: number;
  date: string;
  meet: string;
  bodyweight: number | null;
};

// The marker at the chosen date. `hidden` is the bands' starting point: it's never drawn, it only
// makes sure the x-axis range includes that meet even when the date filter excludes it.
type PredictionPoint = {
  kind: "prediction";
  hidden: boolean;
  t: number;
  value: number;
  prediction: Prediction;
};

const DAY_MS = 24 * 60 * 60 * 1000;
const X_PADDING_MS = 30 * DAY_MS; // keeps a lone point (and the end points) off the axis edges
const DOT_COLOR = "#2563eb";
const PREDICTION_COLOR = "#f59e0b";

// Dates are plain calendar days, so format in UTC to avoid the viewer's timezone shifting them.
function formatTick(t: number) {
  return new Date(t).toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

// The bands: shaded fans that start at one point (the latest meet's total) and widen out to the
// chosen date. The darker fan is the likely range (25th-75th percentile), the lighter one reaches up
// to the 99th percentile, and the dashed line is the median. Drawn with the chart's own axis scales so
// it stays aligned with the dots.
function PredictionBands({ prediction, originTotal }: { prediction: Prediction; originTotal: number }) {
  const xScale = useXAxisScale();
  const yScale = useYAxisScale();
  if (!xScale || !yScale) return null;

  const x0 = xScale(Date.parse(prediction.latest_meet.date)) as number;
  const x1 = xScale(Date.parse(prediction.date)) as number;
  const y = (v: number) => yScale(v) as number;
  const origin = y(originTotal);
  const q = prediction.prediction;
  if ([x0, x1, origin].some((v) => !Number.isFinite(v))) return null;

  return (
    <g pointerEvents="none">
      <polygon points={`${x0},${origin} ${x1},${y(q.q99)} ${x1},${y(q.q75)}`} fill={PREDICTION_COLOR} fillOpacity={0.12} />
      <polygon points={`${x0},${origin} ${x1},${y(q.q75)} ${x1},${y(q.q25)}`} fill={PREDICTION_COLOR} fillOpacity={0.3} />
      <line x1={x0} y1={origin} x2={x1} y2={y(q.q50)} stroke={PREDICTION_COLOR} strokeWidth={2} strokeDasharray="5 4" />
    </g>
  );
}

function ChartTooltip({ active, payload, metric }: { active?: boolean; payload?: ReadonlyArray<{ payload: Point | PredictionPoint }>; metric: Metric }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const box = "rounded-lg border border-black/10 bg-white px-3 py-2 text-xs shadow dark:border-white/10 dark:bg-black";
  const muted = "text-black/60 dark:text-white/60";

  if (p.kind === "prediction") {
    if (p.hidden) return null;
    const { prediction: pr, date, bodyweight, meets_used } = p.prediction;
    return (
      <div className={box}>
        <div className="font-medium">Predicted for {date}</div>
        <div className="mt-1">
          Median: <span className="font-medium">{pr.q50} kg</span>
        </div>
        <div>
          Likely range: {pr.q25}–{pr.q75} kg
        </div>
        <div>99% of outcomes under {pr.q99} kg</div>
        <div className={muted}>
          At {bodyweight} kg, from {meets_used} meet{meets_used === 1 ? "" : "s"}. Assumes no bomb-out.
        </div>
      </div>
    );
  }

  return (
    <div className={box}>
      <div className="font-medium">{p.meet}</div>
      <div className={muted}>{p.date}</div>
      <div className="mt-1">
        {metric}: <span className="font-medium">{p.value} kg</span>
      </div>
      {p.bodyweight != null && <div className={muted}>Bodyweight: {p.bodyweight} kg</div>}
    </div>
  );
}

export default function Graph({
  rows,
  metric,
  prediction,
  originTotal,
}: {
  rows: Meet[];
  metric: Metric;
  // Only passed for the Total graph; null when prediction is off, invalid, or still loading.
  prediction: Prediction | null;
  // Where the bands start: the athlete's latest meet total (their last real total if that meet was a bomb-out).
  originTotal: number | null;
}) {
  const field = METRIC_FIELD[metric];

  const points: Point[] = rows
    .flatMap((r) => {
      // An undated meet has no place on the time axis.
      if (!r.date) return [];
      // A bomb-out's lifts are stored as 0 when missed entirely, so it plots at 0 for Total (and for
      // whichever lift was bombed); if the other lift was made, that real value is plotted instead.
      const value = r[field] ?? (r.bombed_out ? 0 : null);
      if (value == null) return [];
      return [{ kind: "meet" as const, t: Date.parse(r.date), value, date: r.date, meet: r.meet, bodyweight: r.bodyweight }];
    })
    .sort((a, b) => a.t - b.t);

  const showPrediction = prediction !== null && originTotal !== null;
  const predictionPoints: PredictionPoint[] =
    showPrediction
      ? [
          { kind: "prediction", hidden: true, t: Date.parse(prediction.latest_meet.date), value: originTotal, prediction },
          { kind: "prediction", hidden: false, t: Date.parse(prediction.date), value: prediction.prediction.q50, prediction },
        ]
      : [];
  const ceiling = showPrediction ? prediction.prediction.q99 : 0;

  const undated = rows.filter((r) => !r.date).length;

  return (
    <div>
      <div className="h-80 rounded-xl border border-black/10 p-3 text-black/60 dark:border-white/10 dark:text-white/60">
        {points.length === 0 && !showPrediction ? (
          <div className="flex h-full items-center justify-center text-sm">No results to plot.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="currentColor" strokeOpacity={0.1} />
              <XAxis
                dataKey="t"
                type="number"
                name="Date"
                domain={[(min: number) => min - X_PADDING_MS, (max: number) => max + X_PADDING_MS]}
                tickFormatter={formatTick}
                tick={{ fill: "currentColor", fontSize: 12 }}
                stroke="currentColor"
                strokeOpacity={0.3}
              />
              <YAxis
                dataKey="value"
                type="number"
                name={metric}
                domain={[0, (max: number) => Math.ceil(Math.max(max, ceiling) / 10) * 10]}
                width={44}
                tick={{ fill: "currentColor", fontSize: 12 }}
                stroke="currentColor"
                strokeOpacity={0.3}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={(props) => (
                  <ChartTooltip
                    active={props.active}
                    payload={props.payload as ReadonlyArray<{ payload: Point | PredictionPoint }>}
                    metric={metric}
                  />
                )}
              />
              {showPrediction && <PredictionBands prediction={prediction} originTotal={originTotal} />}
              <Scatter data={points} fill={DOT_COLOR} isAnimationActive={false} />
              {showPrediction && (
                <Scatter
                  data={predictionPoints}
                  fill={PREDICTION_COLOR}
                  isAnimationActive={false}
                  shape={(props: { cx?: number; cy?: number; payload?: PredictionPoint }) =>
                    props.payload?.hidden || props.cx == null || props.cy == null ? (
                      <g />
                    ) : (
                      <circle cx={props.cx} cy={props.cy} r={6} fill={PREDICTION_COLOR} stroke="white" strokeWidth={1.5} />
                    )
                  }
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
      {(showPrediction || undated > 0) && (
        <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-black/50 dark:text-white/50">
          {showPrediction && (
            <>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-3 rounded-sm" style={{ backgroundColor: PREDICTION_COLOR, opacity: 0.55 }} />
                likely range (25th–75th percentile)
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-3 rounded-sm" style={{ backgroundColor: PREDICTION_COLOR, opacity: 0.25 }} />
                up to the 99th percentile
              </span>
            </>
          )}
          {undated > 0 && (
            <span>
              {undated} meet{undated === 1 ? "" : "s"} with no date not plotted
            </span>
          )}
        </p>
      )}
    </div>
  );
}

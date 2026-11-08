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
  bombedOut: boolean;
};

// A dot at the chosen date, one per band edge. `hidden` is the bands' starting point: it's never drawn,
// it only makes sure the x-axis range includes that meet even when the date filter excludes it.
type PredictionPoint = {
  kind: "prediction";
  hidden: boolean;
  t: number;
  value: number;
  color: string;
  prediction: Prediction;
};

type Quantile = keyof Prediction["prediction"];

const DAY_MS = 24 * 60 * 60 * 1000;
const X_PADDING_MS = 30 * DAY_MS; // keeps a lone point (and the end points) off the axis edges
// While a prediction is shown, only this much history before the latest meet is plotted.
const ZOOM_WINDOW_MS = 365 * DAY_MS;
const DOT_COLOR = "#2563eb";

// The prediction bands, outermost first: each runs between two neighbouring percentiles.
const BANDS: { label: string; color: string; lo: Quantile; hi: Quantile }[] = [
  { label: "75th–99th percentile", color: "#ef4444", lo: "q75", hi: "q99" },
  { label: "50th–75th percentile", color: "#f97316", lo: "q50", hi: "q75" },
  { label: "25th–50th percentile", color: "#eab308", lo: "q25", hi: "q50" },
];
const BAND_OPACITY = 0.6; // lower, and the three colours blur together on the dark theme
// One dot per band edge, coloured like the band it tops (the 25th is the yellow band's floor).
const EDGE_DOTS: { q: Quantile; color: string }[] = [
  { q: "q99", color: BANDS[0].color },
  { q: "q75", color: BANDS[1].color },
  { q: "q50", color: BANDS[2].color },
  { q: "q25", color: BANDS[2].color },
];

function Swatch({ color }: { color: string }) {
  return <span className="inline-block h-2 w-3 shrink-0 rounded-sm" style={{ backgroundColor: color }} />;
}

// Dates are plain calendar days, so format in UTC to avoid the viewer's timezone shifting them.
function formatTick(t: number) {
  return new Date(t).toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

// The bands (BANDS): shaded fans that start at one point (the latest meet's total) and widen out to
// the chosen date; the dashed line is the median. Drawn with the chart's own axis scales so they stay
// aligned with the dots.
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
      {BANDS.map((b) => (
        <polygon
          key={b.label}
          points={`${x0},${origin} ${x1},${y(q[b.hi])} ${x1},${y(q[b.lo])}`}
          fill={b.color}
          fillOpacity={BAND_OPACITY}
        />
      ))}
      <line x1={x0} y1={origin} x2={x1} y2={y(q.q50)} stroke="currentColor" strokeWidth={1.5} strokeDasharray="5 4" />
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
    const pr = p.prediction.prediction;
    return (
      <div className={`${box} space-y-0.5`}>
        {BANDS.map((b) => (
          <div key={b.label} className="flex items-center gap-1.5">
            <Swatch color={b.color} />
            {b.label}: {pr[b.lo]} to {pr[b.hi]} kg
          </div>
        ))}
        <div className="font-medium">Median: {pr.q50} kg</div>
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
      return [{ kind: "meet" as const, t: Date.parse(r.date), value, date: r.date, meet: r.meet, bodyweight: r.bodyweight, bombedOut: r.bombed_out }];
    })
    .sort((a, b) => a.t - b.t);

  const showPrediction = prediction !== null && originTotal !== null;
  const predictionPoints: PredictionPoint[] =
    showPrediction
      ? [
          { kind: "prediction", hidden: true, t: Date.parse(prediction.latest_meet.date), value: originTotal, color: "", prediction },
          ...EDGE_DOTS.map((d) => ({
            kind: "prediction" as const,
            hidden: false,
            t: Date.parse(prediction.date),
            value: prediction.prediction[d.q],
            color: d.color,
            prediction,
          })),
        ]
      : [];

  // While a prediction is shown the graph zooms in on it, or the bands would be a sliver of a whole
  // career: only the 12 months before the latest meet are plotted (inside whatever date range is set),
  // bomb-outs are left out so the y-axis needn't reach 0, and the y-axis fits those meets and the bands.
  // Otherwise the y-axis starts at 0.
  let plotted = points;
  let yDomain: [number, number | ((max: number) => number)] = [0, (max: number) => Math.ceil(max / 10) * 10];
  let yTicks: number[] | undefined; // round-number ticks for the zoomed axis (Recharts' own land on e.g. 329, 338)
  if (showPrediction) {
    const windowStart = Date.parse(prediction.latest_meet.date) - ZOOM_WINDOW_MS;
    plotted = points.filter((p) => p.t >= windowStart && !p.bombedOut);
    const q = prediction.prediction;
    const values = [...plotted.map((p) => p.value), originTotal, q.q25, q.q99];
    const min = Math.min(...values) - 2;
    const max = Math.max(...values) + 2;
    const step = [5, 10, 20, 25, 50, 100].find((s) => (max - min) / s <= 6) ?? 100;
    const lo = Math.max(0, Math.floor(min / step) * step);
    const hi = Math.ceil(max / step) * step;
    yDomain = [lo, hi];
    yTicks = Array.from({ length: Math.round((hi - lo) / step) + 1 }, (_, i) => lo + i * step);
  }

  const undated = rows.filter((r) => !r.date).length;

  return (
    <div>
      {showPrediction && (
        <p className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-black/60 dark:text-white/60">
          {BANDS.map((b) => (
            <span key={b.label} className="flex items-center gap-1">
              <Swatch color={b.color} />
              {b.label}
            </span>
          ))}
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 border-t-2 border-dashed border-current" />
            median
          </span>
          <span className="text-black/45 dark:text-white/45">Zoomed to the 12 months before the latest meet; bomb-outs hidden</span>
        </p>
      )}
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
                domain={yDomain}
                ticks={yTicks}
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
              <Scatter data={plotted} fill={DOT_COLOR} isAnimationActive={false} />
              {showPrediction && (
                <Scatter
                  data={predictionPoints}
                  isAnimationActive={false}
                  shape={(props: { cx?: number; cy?: number; payload?: PredictionPoint }) =>
                    props.payload?.hidden || props.cx == null || props.cy == null ? (
                      <g />
                    ) : (
                      <circle cx={props.cx} cy={props.cy} r={5} fill={props.payload?.color} stroke="white" strokeWidth={1.5} />
                    )
                  }
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
      {undated > 0 && (
        <p className="mt-2 text-xs text-black/50 dark:text-white/50">
          {undated} meet{undated === 1 ? "" : "s"} with no date not plotted
        </p>
      )}
    </div>
  );
}

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
import { METRIC_FIELD, type GraphPrediction, type GraphSeries, type MarkerShape, type Metric, type Prediction } from "@/lib/athlete";

type Point = {
  kind: "meet";
  t: number;
  value: number;
  date: string;
  meet: string;
  bodyweight: number | null;
  bombedOut: boolean;
  athlete: string;
  color: string;
  shape: MarkerShape;
};

// A dot at the chosen date, one per band edge. `hidden` is the bands' starting point: it's never drawn,
// it only makes sure the x-axis range includes that meet even when the date filter excludes it.
type PredictionPoint = {
  kind: "prediction";
  hidden: boolean;
  t: number;
  value: number;
  color: string;
  label: string; // which percentile this dot is, for its hover
  athlete: string;
};

type Quantile = keyof Prediction["prediction"];

const DAY_MS = 24 * 60 * 60 * 1000;
const X_PADDING_MS = 30 * DAY_MS; // keeps a lone point (and the end points) off the axis edges
// While a prediction is shown, only this much history before the latest meet is plotted.
const ZOOM_WINDOW_MS = 365 * DAY_MS;

// A meet's marker in its athlete's colour and shape (see ATHLETE_STYLES), with a thin ring in the page
// background so overlapping markers stay apart.
function Marker({ cx, cy, color, shape, size = 5 }: { cx: number; cy: number; color: string; shape: MarkerShape; size?: number }) {
  const ring = { stroke: "var(--background)", strokeWidth: 1 };
  if (shape === "square") {
    return <rect x={cx - size} y={cy - size} width={size * 2} height={size * 2} rx={1} fill={color} {...ring} />;
  }
  if (shape === "diamond") {
    const d = size * 1.3;
    return <polygon points={`${cx},${cy - d} ${cx + d},${cy} ${cx},${cy + d} ${cx - d},${cy}`} fill={color} {...ring} />;
  }
  return <circle cx={cx} cy={cy} r={size} fill={color} {...ring} />;
}

// The same marker for legends and tooltips, outside the chart.
function MarkerIcon({ color, shape }: { color: string; shape: MarkerShape }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden className="shrink-0">
      <Marker cx={6} cy={6} color={color} shape={shape} size={4.5} />
    </svg>
  );
}

// The prediction bands, top to bottom: each runs between two neighbouring percentiles, and they mirror
// each other around the median - the athlete's darker colour on the outside, the lighter one inside
// (bandOuter / bandInner in ATHLETE_STYLES).
type BandTone = "outer" | "inner";
const BANDS: { label: string; tone: BandTone; lo: Quantile; hi: Quantile }[] = [
  { label: "75th–99th percentile", tone: "outer", lo: "q75", hi: "q99" },
  { label: "50th–75th percentile", tone: "inner", lo: "q50", hi: "q75" },
  { label: "25th–50th percentile", tone: "inner", lo: "q25", hi: "q50" },
  { label: "1st–25th percentile", tone: "outer", lo: "q1", hi: "q25" },
];
const BAND_OPACITY = 0.6; // lower, and the colours blur together on the dark theme
const BAND_OPACITY_MANY = 0.45; // several athletes' bands can overlap
// One dot per band edge, coloured like the band between it and the median.
const EDGE_DOTS: { q: Quantile; tone: BandTone; label: string }[] = [
  { q: "q99", tone: "outer", label: "99th percentile" },
  { q: "q75", tone: "inner", label: "75th percentile" },
  { q: "q50", tone: "inner", label: "Median (50th percentile)" },
  { q: "q25", tone: "inner", label: "25th percentile" },
  { q: "q1", tone: "outer", label: "1st percentile" },
];
const toneColor = (p: GraphPrediction, tone: BandTone) => (tone === "outer" ? p.bandOuter : p.bandInner);

function Swatch({ color }: { color: string }) {
  return <span className="inline-block h-2 w-3 shrink-0 rounded-sm" style={{ backgroundColor: color }} />;
}

// Dates are plain calendar days, so format in UTC to avoid the viewer's timezone shifting them.
function formatTick(t: number) {
  return new Date(t).toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

// One athlete's bands (BANDS): shaded fans that start at one point (their latest meet's total) and widen
// out to the chosen date; the dotted white line is the median (it runs between the two inner bands, so
// white shows on both themes). Drawn with the chart's own axis scales so they stay aligned with the dots.
function PredictionBands({ p, opacity }: { p: GraphPrediction; opacity: number }) {
  const xScale = useXAxisScale();
  const yScale = useYAxisScale();
  if (!xScale || !yScale) return null;

  const x0 = xScale(Date.parse(p.prediction.latest_meet.date)) as number;
  const x1 = xScale(Date.parse(p.prediction.date)) as number;
  const y = (v: number) => yScale(v) as number;
  const origin = y(p.originTotal);
  const q = p.prediction.prediction;
  if ([x0, x1, origin].some((v) => !Number.isFinite(v))) return null;

  return (
    <g pointerEvents="none">
      {BANDS.map((b) => (
        <polygon
          key={b.label}
          points={`${x0},${origin} ${x1},${y(q[b.hi])} ${x1},${y(q[b.lo])}`}
          fill={toneColor(p, b.tone)}
          fillOpacity={opacity}
        />
      ))}
      <line x1={x0} y1={origin} x2={x1} y2={y(q.q50)} stroke="white" strokeWidth={2} strokeDasharray="0.1 4" strokeLinecap="round" />
    </g>
  );
}

function ChartTooltip({
  active,
  payload,
  metric,
  showAthlete,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload: Point | PredictionPoint }>;
  metric: Metric;
  showAthlete: boolean; // when comparing, say whose meet it is
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const box = "rounded-lg border border-black/10 bg-white px-3 py-2 text-xs shadow dark:border-white/10 dark:bg-black";
  const muted = "text-black/60 dark:text-white/60";

  if (p.kind === "prediction") {
    if (p.hidden) return null;
    // Each dot shows only its own percentile (and, when comparing, whose prediction it is).
    return (
      <div className={box}>
        {showAthlete && <div className="mb-0.5 font-semibold">{p.athlete}</div>}
        <div className="flex items-center gap-1.5">
          <Swatch color={p.color} />
          {p.label}: <span className="font-medium">{p.value} kg</span>
        </div>
      </div>
    );
  }

  return (
    <div className={box}>
      {showAthlete && (
        <div className="mb-1 flex items-center gap-1.5 font-semibold">
          <MarkerIcon color={p.color} shape={p.shape} />
          {p.athlete}
        </div>
      )}
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
  series,
  metric,
  predictions,
}: {
  // The page's athlete first, then any compared athletes, each with its colour and marker shape.
  series: GraphSeries[];
  metric: Metric;
  // One per athlete with an answered prediction (Total graph only; empty when prediction is off).
  predictions: GraphPrediction[];
}) {
  const field = METRIC_FIELD[metric];
  const comparing = series.length > 1;

  const pointsBySeries: Point[][] = series.map((s) =>
    s.rows
      .flatMap((r) => {
        // An undated meet has no place on the time axis.
        if (!r.date) return [];
        // A bomb-out's lifts are stored as 0 when missed entirely, so it plots at 0 for Total (and for
        // whichever lift was bombed); if the other lift was made, that real value is plotted instead.
        const value = r[field] ?? (r.bombed_out ? 0 : null);
        if (value == null) return [];
        return [{
          kind: "meet" as const, t: Date.parse(r.date), value, date: r.date, meet: r.meet, bodyweight: r.bodyweight,
          bombedOut: r.bombed_out, athlete: s.name, color: s.color, shape: s.shape,
        }];
      })
      .sort((a, b) => a.t - b.t),
  );
  const anyPoints = pointsBySeries.some((p) => p.length > 0);

  const showPrediction = predictions.length > 0;
  // Per prediction: a hidden point at its starting meet (so the x-axis always includes it) and a dot at
  // each band edge.
  const predictionPoints: PredictionPoint[] = predictions.flatMap((p) => [
    { kind: "prediction" as const, hidden: true, t: Date.parse(p.prediction.latest_meet.date), value: p.originTotal, color: "", label: "", athlete: p.name },
    ...EDGE_DOTS.map((d) => ({
      kind: "prediction" as const,
      hidden: false,
      t: Date.parse(p.prediction.date),
      value: p.prediction.prediction[d.q],
      color: toneColor(p, d.tone),
      label: d.label,
      athlete: p.name,
    })),
  ]);

  // While a prediction is shown the graph zooms in on it, or the bands would be a sliver of a whole
  // career: only the 12 months before the (earliest predicted athlete's) latest meet are plotted (inside
  // whatever date range is set), bomb-outs are left out so the y-axis needn't reach 0, and the y-axis fits
  // those meets and every athlete's bands. Otherwise the y-axis starts at 0.
  let plotted = pointsBySeries;
  let yDomain: [number, number | ((max: number) => number)] = [0, (max: number) => Math.ceil(max / 10) * 10];
  let yTicks: number[] | undefined; // round-number ticks for the zoomed axis (Recharts' own land on e.g. 329, 338)
  if (showPrediction) {
    const windowStart = Math.min(...predictions.map((p) => Date.parse(p.prediction.latest_meet.date))) - ZOOM_WINDOW_MS;
    plotted = pointsBySeries.map((pts) => pts.filter((p) => p.t >= windowStart && !p.bombedOut));
    const values = [
      ...plotted.flat().map((p) => p.value),
      ...predictions.flatMap((p) => [p.originTotal, p.prediction.prediction.q1, p.prediction.prediction.q99]),
    ];
    const min = Math.min(...values) - 2;
    const max = Math.max(...values) + 2;
    const step = [5, 10, 20, 25, 50, 100].find((s) => (max - min) / s <= 6) ?? 100;
    const lo = Math.max(0, Math.floor(min / step) * step);
    const hi = Math.ceil(max / step) * step;
    yDomain = [lo, hi];
    yTicks = Array.from({ length: Math.round((hi - lo) / step) + 1 }, (_, i) => lo + i * step);
  }

  const undated = series[0]?.rows.filter((r) => !r.date).length ?? 0;

  return (
    <div>
      {comparing && (
        <p className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-black/70 dark:text-white/70">
          {series.map((s) => (
            <span key={s.name} className="flex items-center gap-1.5">
              <MarkerIcon color={s.color} shape={s.shape} />
              {s.name}
            </span>
          ))}
        </p>
      )}
      {showPrediction && (
        <p className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-black/60 dark:text-white/60">
          {/* Each athlete's bands use their own colours: darker outside, lighter inside. */}
          <span className="flex items-center gap-1">
            {predictions.map((p) => <Swatch key={p.name} color={p.bandOuter} />)}
            1st–25th / 75th–99th percentile
          </span>
          <span className="flex items-center gap-1">
            {predictions.map((p) => <Swatch key={p.name} color={p.bandInner} />)}
            25th–75th
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-flex h-2 w-4 items-center rounded-sm px-0.5" style={{ backgroundColor: predictions[0].bandInner }}>
              <span className="w-full border-t-2 border-dotted border-white" />
            </span>
            median
          </span>
          <span className="text-black/45 dark:text-white/45">Zoomed to the 12 months before the latest meet; bomb-outs hidden</span>
        </p>
      )}
      <div className="h-80 rounded-xl border border-black/10 p-3 text-black/60 dark:border-white/10 dark:text-white/60">
        {!anyPoints && !showPrediction ? (
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
                    showAthlete={comparing}
                  />
                )}
              />
              {predictions.map((p) => (
                <PredictionBands key={p.name} p={p} opacity={predictions.length > 1 ? BAND_OPACITY_MANY : BAND_OPACITY} />
              ))}
              {/* zIndex puts the page's own athlete on top of compared ones (Recharts' default is 600). */}
              {plotted.map((pts, i) => {
                const s = series[i];
                return (
                  <Scatter
                    key={s.name}
                    name={s.name}
                    data={pts}
                    zIndex={600 + series.length - i}
                    isAnimationActive={false}
                    shape={(props: { cx?: number; cy?: number }) =>
                      props.cx == null || props.cy == null ? <g /> : <Marker cx={props.cx} cy={props.cy} color={s.color} shape={s.shape} />
                    }
                  />
                );
              })}
              {showPrediction && (
                <Scatter
                  data={predictionPoints}
                  zIndex={700}
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

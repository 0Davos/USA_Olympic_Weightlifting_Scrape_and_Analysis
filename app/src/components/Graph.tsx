"use client";

import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { METRIC_FIELD, type Meet, type Metric } from "@/lib/athlete";

type Point = {
  t: number;
  value: number;
  date: string;
  meet: string;
  bodyweight: number | null;
};

const DAY_MS = 24 * 60 * 60 * 1000;
const X_PADDING_MS = 30 * DAY_MS; // keeps a lone point (and the end points) off the axis edges
const DOT_COLOR = "#2563eb";

// Dates are plain calendar days, so format in UTC to avoid the viewer's timezone shifting them.
function formatTick(t: number) {
  return new Date(t).toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

function ChartTooltip({ active, payload, metric }: { active?: boolean; payload?: ReadonlyArray<{ payload: Point }>; metric: Metric }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs shadow dark:border-white/10 dark:bg-black">
      <div className="font-medium">{p.meet}</div>
      <div className="text-black/60 dark:text-white/60">{p.date}</div>
      <div className="mt-1">
        {metric}: <span className="font-medium">{p.value} kg</span>
      </div>
      {p.bodyweight != null && <div className="text-black/60 dark:text-white/60">Bodyweight: {p.bodyweight} kg</div>}
    </div>
  );
}

export default function Graph({ rows, metric }: { rows: Meet[]; metric: Metric }) {
  const field = METRIC_FIELD[metric];

  const points: Point[] = rows
    .flatMap((r) => {
      // An undated meet has no place on the time axis.
      if (!r.date) return [];
      // A bomb-out's lifts are stored as 0 when missed entirely, so it plots at 0 for Total (and for
      // whichever lift was bombed); if the other lift was made, that real value is plotted instead.
      const value = r[field] ?? (r.bombed_out ? 0 : null);
      if (value == null) return [];
      return [{ t: Date.parse(r.date), value, date: r.date, meet: r.meet, bodyweight: r.bodyweight }];
    })
    .sort((a, b) => a.t - b.t);

  const undated = rows.filter((r) => !r.date).length;

  return (
    <div>
      <div className="h-80 rounded-xl border border-black/10 p-3 text-black/60 dark:border-white/10 dark:text-white/60">
        {points.length === 0 ? (
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
                domain={[0, "auto"]}
                width={44}
                tick={{ fill: "currentColor", fontSize: 12 }}
                stroke="currentColor"
                strokeOpacity={0.3}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={(props) => (
                  <ChartTooltip active={props.active} payload={props.payload as ReadonlyArray<{ payload: Point }>} metric={metric} />
                )}
              />
              <Scatter data={points} fill={DOT_COLOR} isAnimationActive={false} />
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

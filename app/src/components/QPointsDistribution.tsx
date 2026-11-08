"use client";

import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Distribution } from "@/lib/rankings";

// The shaded bands, lowest first. Colours are CSS variables (globals.css) so dark mode gets its own,
// separately validated ramp.
const BANDS = [
  { label: "Bottom 25%", color: "var(--dist-1)" },
  { label: "25th–50th", color: "var(--dist-2)" },
  { label: "50th–75th", color: "var(--dist-3)" },
  { label: "75th–90th", color: "var(--dist-4)" },
  { label: "Top 10%", color: "var(--dist-5)" },
];

// The chart's fixed height, shared with the loading placeholder so nothing jumps when data arrives.
export const DISTRIBUTION_CHART_CLASS = "h-48";

function ordinal(p: number) {
  return p === 50 ? "Median" : `${p}th`;
}

type Point = { x: number; athletes: number; lo: number | null };

function bandFor(q: number, cutoffs: number[]) {
  const i = cutoffs.slice(0, 4).findIndex((c) => q < c);
  return BANDS[i === -1 ? 4 : i];
}

// The cutoff values and the band key under the chart. `invisible` renders the same text (with placeholder
// numbers) but hidden, so the loading placeholder wraps onto exactly as many lines as the real thing.
function Key({ percentiles, invisible }: { percentiles: Distribution["percentiles"]; invisible?: boolean }) {
  return (
    <div className={invisible ? "invisible" : ""} aria-hidden={invisible}>
      <p className="mt-2 text-xs text-black/60 dark:text-white/60">
        {percentiles.map((p, i) => (
          <span key={p.p}>
            {i > 0 && " · "}
            {ordinal(p.p)} <span className="font-medium text-black/80 dark:text-white/80">{Math.round(p.q_points)}</span>
          </span>
        ))}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-black/60 dark:text-white/60">
        {BANDS.map((b) => (
          <span key={b.label} className="flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm" style={{ backgroundColor: b.color }} />
            {b.label}
          </span>
        ))}
      </div>
    </div>
  );
}

const PLACEHOLDER_PERCENTILES = [25, 50, 75, 90, 99].map((p) => ({ p, q_points: 888 }));

export default function QPointsDistribution({ data, id }: { data: Distribution | null; id: string }) {
  if (!data) {
    return (
      <div>
        <div className={`${DISTRIBUTION_CHART_CLASS} rounded-lg bg-black/[0.03] dark:bg-white/[0.04]`} aria-hidden />
        <Key percentiles={PLACEHOLDER_PERCENTILES} invisible />
      </div>
    );
  }
  const w = data.bin_width;
  const cutoffs = data.percentiles.map((p) => p.q_points);
  const min = data.bins[0]?.lo ?? 0;
  const max = (data.bins.at(-1)?.lo ?? 0) + w;
  // One point per bin at its middle, plus zero at both ends so the curve starts and ends on the baseline.
  const points: Point[] = [
    { x: min, athletes: 0, lo: null },
    ...data.bins.map((b) => ({ x: b.lo + w / 2, athletes: b.athletes, lo: b.lo })),
    { x: max, athletes: 0, lo: null },
  ];

  // The fill changes colour at each band cutoff: a horizontal gradient with hard stops, positioned as a
  // fraction of the curve's width (which spans exactly min..max).
  const at = (q: number) => Math.min(1, Math.max(0, (q - min) / (max - min)));
  const edges = [0, ...cutoffs.slice(0, 4).map(at), 1];
  const gradientId = `dist-${id}`;

  return (
    <div>
      <div className={`${DISTRIBUTION_CHART_CLASS} text-black/60 dark:text-white/60`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 30, right: 8, bottom: 0, left: 8 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                {BANDS.flatMap((b, i) => [
                  <stop key={`${i}a`} offset={edges[i]} style={{ stopColor: b.color }} />,
                  <stop key={`${i}b`} offset={edges[i + 1]} style={{ stopColor: b.color }} />,
                ])}
              </linearGradient>
            </defs>
            <XAxis
              dataKey="x"
              type="number"
              domain={[min, max]}
              tickCount={6}
              allowDecimals={false}
              tick={{ fill: "currentColor", fontSize: 11 }}
              stroke="currentColor"
              strokeOpacity={0.3}
            />
            <YAxis hide domain={[0, "dataMax"]} />
            <Tooltip
              cursor={{ stroke: "currentColor", strokeOpacity: 0.3 }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as Point | undefined;
                if (!active || !p || p.lo == null) return null;
                const band = bandFor(p.lo + w / 2, cutoffs);
                return (
                  <div className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs shadow dark:border-white/10 dark:bg-black">
                    <div className="font-medium">
                      {p.lo}–{p.lo + w} Q-points: {p.athletes.toLocaleString()} athlete{p.athletes === 1 ? "" : "s"}
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-black/60 dark:text-white/60">
                      <span className="inline-block h-2 w-3 rounded-sm" style={{ backgroundColor: band.color }} />
                      {band.label}
                    </div>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="athletes"
              stroke="currentColor"
              strokeOpacity={0.5}
              strokeWidth={1}
              fill={`url(#${gradientId})`}
              fillOpacity={1}
              isAnimationActive={false}
              activeDot={{ r: 3 }}
            />
            {data.percentiles.map((p, i) => (
              <ReferenceLine
                key={p.p}
                x={p.q_points}
                stroke="currentColor"
                strokeOpacity={0.6}
                strokeDasharray="3 3"
                // Neighbouring cutoffs can sit a few pixels apart, so the labels alternate between two
                // heights instead of overlapping.
                label={({ viewBox }: { viewBox?: { x?: number; y?: number } }) => (
                  <text
                    x={viewBox?.x ?? 0}
                    y={(viewBox?.y ?? 0) - (i % 2 ? 4 : 16)}
                    textAnchor="middle"
                    fill="currentColor"
                    fontSize={10}
                  >
                    {ordinal(p.p)}
                  </text>
                )}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <Key percentiles={data.percentiles} />
    </div>
  );
}

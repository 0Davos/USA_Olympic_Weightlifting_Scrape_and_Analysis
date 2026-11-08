"use client";

import { useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BOX_CLASS, ErrorOverlay, useLoad } from "./QPointsLists";
import { fetchAthleteStats, type AthleteStats } from "@/lib/rankings";

// The two bar charts at the bottom of the home page: new athletes per year and meets per athlete.
// One series each, so no legend; the title names it and each bar has a hover.
const load = (_: "all", signal: AbortSignal) => fetchAthleteStats(signal);

const CHART_CLASS = "h-56"; // shared with the loading placeholder so nothing jumps
const BAR_COLOR = "var(--dist-3)"; // the mid blue of the Q-point spread charts, set for light and dark
const SUBTITLE_CLASS = "mt-1 text-xs text-black/50 dark:text-white/50";

type Point = { label: string; athletes: number; note?: string; partial?: boolean };

function Bars({ points, unit }: { points: Point[]; unit: (p: Point) => string }) {
  return (
    <div className={`${CHART_CLASS} text-black/60 dark:text-white/60`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: 4 }} barCategoryGap={2}>
          <XAxis
            dataKey="label"
            interval="preserveStartEnd"
            minTickGap={12}
            tick={{ fill: "currentColor", fontSize: 11 }}
            stroke="currentColor"
            strokeOpacity={0.3}
            tickLine={false}
          />
          <YAxis
            width={44}
            tick={{ fill: "currentColor", fontSize: 11 }}
            tickFormatter={(v: number) => (v >= 1000 ? `${v / 1000}k` : String(v))}
            stroke="currentColor"
            strokeOpacity={0.3}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "currentColor", fillOpacity: 0.06 }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as Point | undefined;
              if (!active || !p) return null;
              return (
                <div className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs shadow dark:border-white/10 dark:bg-black">
                  <div className="font-medium">{unit(p)}</div>
                  <div className="mt-0.5 text-black/60 dark:text-white/60">
                    {p.athletes.toLocaleString()} athlete{p.athletes === 1 ? "" : "s"}
                    {p.note ? ` (${p.note})` : ""}
                  </div>
                </div>
              );
            }}
          />
          <Bar dataKey="athletes" fill={BAR_COLOR} radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {points.map((p) => (
              <Cell key={p.label} fillOpacity={p.partial ? 0.45 : 1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Placeholder() {
  return <div className={`${CHART_CLASS} rounded-lg bg-black/[0.03] dark:bg-white/[0.04]`} aria-hidden />;
}

export default function AthleteStatsCharts() {
  const [attempt, setAttempt] = useState(0);
  const stats = useLoad<AthleteStats, "all">(load, "all", attempt);
  const data = stats?.status === "ready" ? stats.data : null;
  const failed = stats?.status === "error";
  const retry = () => setAttempt((a) => a + 1);

  const years: Point[] = (data?.new_per_year ?? []).map((y) => ({
    label: String(y.year),
    athletes: y.athletes,
    partial: y.year === data?.current_year,
    note: y.year === data?.current_year ? "so far" : y.year === data?.new_per_year[0]?.year ? "includes everyone already competing" : undefined,
  }));
  const meets: Point[] = (data?.meets_per_athlete ?? []).map((m) => ({ label: String(m.meets), athletes: m.athletes }));
  const more = data?.more_meets;

  return (
    <div className="mt-10 grid gap-6 sm:grid-cols-2">
      <section className={`relative ${BOX_CLASS}`}>
        <h2 className="text-lg font-semibold">New athletes per year</h2>
        <p className={SUBTITLE_CLASS}>
          Each athlete counted in the year of their first meet. Records begin in 2012, so that year includes everyone
          already competing; {data?.current_year ?? "this year"} is so far.
        </p>
        <div className={`mt-3 ${failed ? "invisible" : ""}`}>
          {data ? <Bars points={years} unit={(p) => `First meet in ${p.label}`} /> : <Placeholder />}
        </div>
        {failed && <ErrorOverlay what="chart" onRetry={retry} />}
      </section>

      <section className={`relative ${BOX_CLASS}`}>
        <h2 className="text-lg font-semibold">Meets per athlete</h2>
        <p className={SUBTITLE_CLASS}>
          How many meets each athlete has attended, all time (bomb-outs included).{" "}
          <span className={more ? "" : "invisible"}>
            Plus {more ? more.athletes.toLocaleString() : "000"} athletes with more than 30
            {more?.most ? ` (the most: ${more.most})` : ""}.
          </span>
        </p>
        <div className={`mt-3 ${failed ? "invisible" : ""}`}>
          {data ? (
            <Bars points={meets} unit={(p) => `${p.label} meet${p.label === "1" ? "" : "s"}`} />
          ) : (
            <Placeholder />
          )}
        </div>
        {failed && <ErrorOverlay what="chart" onRetry={retry} />}
      </section>
    </div>
  );
}

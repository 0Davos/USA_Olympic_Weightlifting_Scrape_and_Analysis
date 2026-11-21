"use client";

import { useState } from "react";
import QPointsDistribution from "./QPointsDistribution";
import { BOX_CLASS, ErrorOverlay, PeriodToggle, useLoad } from "./QPointsLists";
import { fetchDistributions, type Distributions, type RankingWindow } from "@/lib/rankings";

// The Q-point spread chart per gender, with its own Past year / All time toggle.
export default function QPointsSpread() {
  const [period, setPeriod] = useState<RankingWindow>("year");
  const [attempt, setAttempt] = useState(0);
  const distributions = useLoad<Distributions>(fetchDistributions, period, attempt);
  const retry = () => setAttempt((a) => a + 1);

  const dists = distributions?.status === "ready" ? distributions.data : null;
  const inPeriod = period === "year" ? " in the past year" : "";

  return (
    <div>
      <PeriodToggle period={period} onChange={setPeriod} />

      <div className="grid gap-6 sm:grid-cols-2">
        {(["men", "women"] as const).map((g) => (
          <section key={g} className={`relative ${BOX_CLASS}`}>
            <h2 className="text-lg font-semibold">{g === "men" ? "Men" : "Women"} — Q-point spread</h2>
            <p className={`mt-1 text-xs text-black/50 dark:text-white/50 ${dists ? "" : "invisible"}`}>
              {dists ? dists[g].athletes.toLocaleString() : "00,000"} athletes&apos; best results{inPeriod}
            </p>
            <div className={`mt-3 ${distributions?.status === "error" ? "invisible" : ""}`}>
              <QPointsDistribution data={dists ? dists[g] : null} id={g} />
            </div>
            {distributions?.status === "error" && <ErrorOverlay what="chart" onRetry={retry} />}
          </section>
        ))}
      </div>
    </div>
  );
}

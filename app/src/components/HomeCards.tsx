"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AthleteSearch from "./AthleteSearch";
import { BOX_CLASS, MUTED_CLASS } from "./QPointsLists";

// Cards that link somewhere are clickable as a whole and go where the header button of the same name goes.
const LINK_CARD_CLASS = `${BOX_CLASS} block transition-colors hover:border-black/30 hover:bg-black/[0.02] dark:hover:border-white/30 dark:hover:bg-white/[0.03]`;
const BODY_CLASS = "mt-2 text-sm leading-6 text-black/70 dark:text-white/70";
const MORE_CLASS = "mt-4 inline-block text-sm font-medium";

// The home page's four feature cards, prediction first. The athlete card holds its own search box instead
// of being a link.
export default function HomeCards() {
  const router = useRouter();

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <section className={BOX_CLASS}>
        <h2 className="text-lg font-semibold">Athlete pages</h2>
        <p className={BODY_CLASS}>
          A prediction of any lifter&apos;s total at their next meet. Each page also has
          their full competition history and a graph of every snatch, clean &amp; jerk and total.
        </p>
        <AthleteSearch
          idPrefix="home-athlete"
          className="mt-4"
          onSelect={(name) => router.push(`/athlete/${encodeURIComponent(name)}`)}
        />
      </section>

      <Link href="/rankings" className={LINK_CARD_CLASS}>
        <h2 className="text-lg font-semibold">Rankings</h2>
        <p className={BODY_CLASS}>The best Q-points results and the fastest improvers.</p>
        <span className={MORE_CLASS}>View rankings →</span>
      </Link>

      <Link href="/stats" className={LINK_CARD_CLASS}>
        <h2 className="text-lg font-semibold">Stats &amp; Graphs</h2>
        <p className={BODY_CLASS}>How US lifters are spread out, and how the sport has grown.</p>
        <span className={MORE_CLASS}>View stats &amp; graphs →</span>
      </Link>

      <section className={BOX_CLASS}>
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-black/50 dark:text-white/50">Meet results</h2>
          <span className="rounded-full border border-black/10 px-2 py-0.5 text-xs text-black/60 dark:border-white/20 dark:text-white/60">
            Coming soon
          </span>
        </div>
        <p className={`mt-2 ${MUTED_CLASS}`}>Every result from a meet, by weight class.</p>
      </section>
    </div>
  );
}

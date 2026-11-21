"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { SITE_NAME } from "@/lib/site";
import AthleteSearch from "./AthleteSearch";
import ThemeToggle from "./ThemeToggle";

export default function TopBar() {
  const router = useRouter();

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-white/90 backdrop-blur dark:border-white/40 dark:bg-black/90">
      {/* On phones the search box wraps onto its own full-width row; from sm up it sits beside the button. */}
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-xl font-semibold tracking-tight">
            {SITE_NAME}
          </Link>
          <ThemeToggle />
        </div>

        <Link
          href="/stats"
          className="ml-auto shrink-0 rounded-lg border border-black/10 px-3 py-1.5 text-sm hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
        >
          Stats &amp; Graphs
        </Link>
        <AthleteSearch
          idPrefix="athlete"
          className="w-full sm:w-auto sm:max-w-xs sm:flex-1"
          onSelect={(name) => router.push(`/athlete/${encodeURIComponent(name)}`)}
        />
      </div>
    </header>
  );
}

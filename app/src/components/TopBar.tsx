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
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-xl font-semibold tracking-tight">
            {SITE_NAME}
          </Link>
          <ThemeToggle />
        </div>

        <AthleteSearch
          idPrefix="athlete"
          className="w-full max-w-xs"
          onSelect={(name) => router.push(`/athlete/${encodeURIComponent(name)}`)}
        />
      </div>
    </header>
  );
}

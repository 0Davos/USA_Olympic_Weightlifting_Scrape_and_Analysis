"use client";

import { useState } from "react";
import Link from "next/link";

export default function TopBar() {
  const [query, setQuery] = useState("");

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-white/90 backdrop-blur dark:border-white/10 dark:bg-black/90">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          [Site Name]
        </Link>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search an athlete..."
          className="w-full max-w-xs rounded-full border border-black/10 bg-transparent px-4 py-2 text-sm outline-none focus:border-black/30 dark:border-white/10 dark:focus:border-white/30"
        />
      </div>
    </header>
  );
}

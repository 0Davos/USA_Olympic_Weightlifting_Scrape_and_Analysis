"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { SITE_NAME } from "@/lib/site";
import AthleteSearch from "./AthleteSearch";
import ThemeToggle from "./ThemeToggle";

const PAGES = [
  { href: "/rankings", label: "Rankings" },
  { href: "/stats", label: "Stats & Graphs" },
  { href: "/compare", label: "Compare" },
] as const;

const NAV_BUTTON_CLASS =
  "rounded-lg border border-black/10 px-3 py-1.5 text-sm hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10";
const NAV_BUTTON_CURRENT_CLASS = "bg-black/5 dark:bg-white/10";

export default function TopBar() {
  const router = useRouter();
  const pathname = usePathname();

  // The phone menu (below md the page buttons don't fit beside the title, so they live behind ☰).
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-white/90 backdrop-blur dark:border-white/40 dark:bg-black/90">
      {/* Below md: title, theme toggle and ☰ on the first row, the search box full width under them.
          From md up: one row, with the page buttons beside the search box. */}
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-xl font-semibold tracking-tight">
            {SITE_NAME}
          </Link>
          <ThemeToggle />
        </div>

        <nav className="ml-auto hidden shrink-0 items-center gap-2 md:flex" aria-label="Pages">
          {PAGES.map((p) => {
            const current = pathname === p.href;
            return (
              <Link
                key={p.href}
                href={p.href}
                aria-current={current ? "page" : undefined}
                className={`${NAV_BUTTON_CLASS} ${current ? NAV_BUTTON_CURRENT_CLASS : ""}`}
              >
                {p.label}
              </Link>
            );
          })}
        </nav>

        <div ref={menuRef} className="relative ml-auto md:hidden">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-controls="phone-menu"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-black/10 text-lg dark:border-white/20"
          >
            {menuOpen ? "×" : "☰"}
          </button>
          {menuOpen && (
            <nav
              id="phone-menu"
              aria-label="Pages"
              className="absolute right-0 top-full mt-2 flex w-48 flex-col overflow-hidden rounded-xl border border-black/10 bg-white text-sm shadow-lg dark:border-white/20 dark:bg-black"
            >
              {PAGES.map((p) => {
                const current = pathname === p.href;
                return (
                  <Link
                    key={p.href}
                    href={p.href}
                    onClick={() => setMenuOpen(false)}
                    aria-current={current ? "page" : undefined}
                    className={`px-4 py-3 hover:bg-black/5 dark:hover:bg-white/10 ${current ? "font-semibold" : ""}`}
                  >
                    {p.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </div>

        <AthleteSearch
          idPrefix="athlete"
          className="w-full md:w-auto md:max-w-xs md:flex-1"
          onSelect={(name) => router.push(`/athlete/${encodeURIComponent(name)}`)}
        />
      </div>
    </header>
  );
}

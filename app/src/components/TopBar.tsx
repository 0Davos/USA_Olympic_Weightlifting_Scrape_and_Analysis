"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const DEBOUNCE_MS = 250;

// The outcome of one search, tagged with the query it answered. The component only shows a
// result whose query matches what's currently typed, so stale results never flash up and
// "loading" is simply "no result for the current text yet".
type SearchResult = { q: string; names: string[]; error: boolean };

export default function TopBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  const trimmed = query.trim();
  const current = result && result.q === trimmed ? result : null;
  const names = current?.names ?? [];
  const showDropdown = open && trimmed !== "";

  // Debounced search: wait for a pause in typing, and cancel the previous request if the
  // text changes again before it finishes.
  useEffect(() => {
    if (!trimmed) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/athletes/search?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`search failed: ${res.status}`);
        const data: { names: string[] } = await res.json();
        setResult({ q: trimmed, names: data.names, error: false });
        setHighlighted(-1);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setResult({ q: trimmed, names: [], error: true });
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [trimmed]);

  // Close the dropdown when clicking anywhere outside the search box.
  useEffect(() => {
    function onPointerDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  function goToAthlete(name: string) {
    setOpen(false);
    setQuery("");
    router.push(`/athlete/${encodeURIComponent(name)}`);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlighted((h) => (names.length ? (h + 1) % names.length : -1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => (names.length ? (h <= 0 ? names.length - 1 : h - 1) : -1));
    } else if (e.key === "Enter") {
      const pick = highlighted >= 0 ? names[highlighted] : names[0];
      if (pick) goToAthlete(pick);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  let message: string | null = null;
  if (showDropdown) {
    if (!current) message = "Searching...";
    else if (current.error) message = "Search is unavailable right now.";
    else if (names.length === 0) message = "No athletes found.";
  }

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-white/90 backdrop-blur dark:border-white/10 dark:bg-black/90">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          [Site Name]
        </Link>

        <div ref={containerRef} className="relative w-full max-w-xs">
          <input
            type="text"
            role="combobox"
            aria-expanded={showDropdown}
            aria-controls="athlete-suggestions"
            aria-autocomplete="list"
            aria-activedescendant={highlighted >= 0 ? `athlete-option-${highlighted}` : undefined}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            placeholder="Search an athlete..."
            className="w-full rounded-full border border-black/10 bg-transparent px-4 py-2 text-sm outline-none focus:border-black/30 dark:border-white/10 dark:focus:border-white/30"
          />

          {showDropdown && (
            <ul
              id="athlete-suggestions"
              role="listbox"
              className="absolute left-0 right-0 top-full mt-2 overflow-hidden rounded-xl border border-black/10 bg-white text-sm shadow-lg dark:border-white/10 dark:bg-black"
            >
              {message ? (
                <li role="presentation" className="px-4 py-2 text-black/50 dark:text-white/50">
                  {message}
                </li>
              ) : (
                names.map((name, i) => (
                  <li
                    key={name}
                    id={`athlete-option-${i}`}
                    role="option"
                    aria-selected={i === highlighted}
                    // mousedown (not click) so the choice lands before the input loses focus
                    onMouseDown={(e) => {
                      e.preventDefault();
                      goToAthlete(name);
                    }}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`cursor-pointer px-4 py-2 ${
                      i === highlighted ? "bg-black/5 dark:bg-white/10" : ""
                    }`}
                  >
                    {name}
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      </div>
    </header>
  );
}

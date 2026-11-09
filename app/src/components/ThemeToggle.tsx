"use client";

import { useEffect, useLayoutEffect } from "react";
import { applyTheme, deviceTheme, saveTheme, savedTheme, type Theme } from "@/lib/theme";

// Day/night switch in the header. The inline script in the root layout has already applied the right
// theme before paint; this button flips it and remembers the choice. The icon is chosen by CSS from the
// same data-theme attribute (a moon in day mode, a sun in night mode), so it's right from the first
// paint and the button needs no React state.
export default function ThemeToggle() {
  // React's dev-mode remount clears the attribute the inline script set; put it back before paint.
  // (A no-op in production.)
  useLayoutEffect(() => {
    applyTheme(savedTheme() ?? deviceTheme());
  }, []);

  // With no saved choice, keep following the device if its setting changes while the page is open.
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return;
    const onChange = () => {
      if (!savedTheme()) applyTheme(deviceTheme());
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  function toggle() {
    const next: Theme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    saveTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Switch between day and night mode"
      title="Click me!" // the hover text (requested 2026-11-08); the aria-label says what it does
      className="flex h-6 w-6 items-center justify-center rounded-md text-black/60 hover:bg-black/5 hover:text-black dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
    >
      <svg className="dark:hidden" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
      <svg className="hidden dark:block" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
    </button>
  );
}

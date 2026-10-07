"use client";

import { useEffect } from "react";

// Fire-and-forget request on first page load so the API function's cold start is paid
// before the user starts typing in the search box. The result is ignored on purpose, and a
// failure must never surface to the user.
export default function WarmUp() {
  useEffect(() => {
    fetch("/api/health").catch(() => {});
  }, []);

  return null;
}

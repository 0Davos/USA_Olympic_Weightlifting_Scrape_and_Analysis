"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ATHLETE_STYLES,
  compareUrl,
  fetchHistory,
  MAX_ON_GRAPH,
  nameKey,
  type AthleteHistory,
} from "@/lib/athlete";
import AthleteGraph, { type GraphAthlete } from "./AthleteGraph";
import AthleteSearch from "./AthleteSearch";

// An athlete's history, by the name in the URL (or as picked).
type HistoryLoad = { status: "ready"; data: AthleteHistory } | { status: "notfound" } | { status: "error" };

export const COMPARE_PLACEHOLDER_CLASS =
  "flex h-80 items-center justify-center rounded-xl border border-black/10 px-6 text-center text-sm text-black/50 dark:border-white/10 dark:text-white/50";

const cleanName = (n: string) => n.replace(/\s+/g, " ").trim();

// The athletes the URL asks for (`?athlete=A&athlete=B`): blanks and repeats dropped, at most MAX_ON_GRAPH.
function namesFromParams(params: URLSearchParams): string[] {
  const seen = new Set<string>();
  const names: string[] = [];
  for (const raw of params.getAll("athlete")) {
    const n = cleanName(raw);
    if (!n || seen.has(nameKey(n))) continue;
    seen.add(nameKey(n));
    names.push(n);
    if (names.length >= MAX_ON_GRAPH) break;
  }
  return names;
}

// The Compare page: up to MAX_ON_GRAPH athletes on one graph, all equal - any can be removed and others
// added. The URL holds the list, so refreshing, going back and sharing the link all keep the comparison.
export default function CompareView() {
  const searchParams = useSearchParams();
  const urlNames = namesFromParams(new URLSearchParams(searchParams.toString()));
  const urlKey = urlNames.join("\n");

  // slots[i] is the athlete in colour slot i (ATHLETE_STYLES[i]), or null if that slot is free, so removing
  // one athlete never repaints another. The URL lists the athletes in slot order, so a refreshed or shared
  // link keeps the colours (apart from closing any gap).
  const [slots, setSlots] = useState<(string | null)[]>(urlNames);
  // When the URL changes from outside (e.g. the header's Compare link), start again from it - but not when
  // it's the change this page just wrote. useSearchParams catches up a render after replaceState, so
  // comparing against the URL on every render would briefly see the old list and reset the slots.
  const [prevUrlKey, setPrevUrlKey] = useState(urlKey);
  const [writtenKey, setWrittenKey] = useState<string | null>(null);
  if (urlKey !== prevUrlKey) {
    setPrevUrlKey(urlKey);
    if (urlKey !== writtenKey) setSlots(urlNames);
  }

  function commit(next: (string | null)[]) {
    while (next.length && next[next.length - 1] == null) next.pop();
    const names = next.filter((n): n is string => n != null);
    setSlots(next);
    setWrittenKey(names.join("\n"));
    // Replace rather than push: adding or removing an athlete isn't a new page, so Back leaves the page.
    window.history.replaceState(null, "", compareUrl(names));
  }

  function add(picked: string) {
    const n = cleanName(picked);
    if (!n || slots.some((s) => s != null && nameKey(s) === nameKey(n))) return;
    const free = slots.indexOf(null);
    const slot = free >= 0 ? free : slots.length;
    if (slot >= MAX_ON_GRAPH) return;
    const next = [...slots];
    next[slot] = n;
    commit(next);
  }

  function remove(id: string) {
    commit(slots.map((s) => (s === id ? null : s)));
  }

  // Each athlete's history, fetched once (again after a retry). Reading the loads through a ref keeps one
  // athlete's answer from cancelling another's request still in flight.
  const [loads, setLoads] = useState<Record<string, HistoryLoad>>({});
  const [retry, setRetry] = useState(0);
  const loadsRef = useRef(loads);
  useEffect(() => {
    loadsRef.current = loads;
  }, [loads]);

  const names = slots.filter((n): n is string => n != null);
  const namesKey = names.join("\n");
  useEffect(() => {
    const missing = names.filter((n) => !(n in loadsRef.current));
    if (missing.length === 0) return;
    const controller = new AbortController();
    for (const n of missing) {
      fetchHistory(n, controller.signal)
        .then((data) => setLoads((m) => ({ ...m, [n]: data ? { status: "ready", data } : { status: "notfound" } })))
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setLoads((m) => ({ ...m, [n]: { status: "error" } }));
        });
    }
    return () => controller.abort();
    // namesKey stands for `names` (a new array every render)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [namesKey, retry]);

  function retryLoad(id: string) {
    setLoads((m) => {
      const rest = { ...m };
      delete rest[id];
      loadsRef.current = rest; // so the effect sees it as missing straight away
      return rest;
    });
    setRetry((r) => r + 1);
  }

  const athletes: GraphAthlete[] = slots.flatMap((n, i) => {
    if (n == null) return [];
    const l = loads[n];
    const history = l?.status === "ready" ? l.data : null;
    return [
      {
        id: n,
        name: history ? history.name : n,
        href: history ? `/athlete/${encodeURIComponent(history.name)}` : undefined,
        style: ATHLETE_STYLES[i],
        history,
        status: l ? l.status : "loading",
        removable: true,
      },
    ];
  });

  const full = names.length >= MAX_ON_GRAPH;

  return (
    <div className="mt-6 flex flex-col gap-6">
      <div>
        {full ? (
          <p className="text-sm text-black/60 dark:text-white/60">
            Up to {MAX_ON_GRAPH} athletes can be compared. Remove one to add another.
          </p>
        ) : (
          <AthleteSearch
            idPrefix="compare-add"
            placeholder={names.length ? "Add another athlete..." : "Add an athlete to compare..."}
            className="w-full max-w-sm"
            onSelect={add}
          />
        )}
      </div>

      {athletes.length === 0 ? (
        <div className={COMPARE_PLACEHOLDER_CLASS}>
          Search for up to {MAX_ON_GRAPH} athletes to compare their results and predictions on one graph.
        </div>
      ) : (
        <>
          <AthleteGraph athletes={athletes} onRemove={remove} onRetry={retryLoad} />
          <p className="text-xs text-black/50 dark:text-white/50">
            The address in your browser keeps this comparison: copy it to share or come back to it.
          </p>
        </>
      )}
    </div>
  );
}

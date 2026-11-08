"""Proves the home page's Q-points rankings (app/api/_rankings.py) are exact.

The API ranks only the best 40 athletes per gender under the cheap rules, then applies the jump rule and
the hand-kept lists to those athletes' histories (checking every result in SQL was too slow). This script
fetches every real result and applies all the rules to everyone, the slow way, and checks both give the
same top 10s, for both windows. Also checks the hand-kept list entries each match exactly one stored
result (a typo would silently do nothing).

Needs SUPABASE_DB_URL in the repo-root .env and network access (it downloads ~310K rows). Read-only.
Run from the repo root:  python tests/check_rankings.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api"))

import index  # noqa: E402  (also loads the repo-root .env)
import _rankings as R  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def fetch_all(cur):
    cur.execute("SET statement_timeout = 120000")
    cur.execute(R.history_query(index.NAME_KEY_SQL, index.NAME_DISPLAY_SQL).replace(
        f"{index.NAME_KEY_SQL} = ANY(%(keys)s) AND ", ""))
    return cur.fetchall()


def brute_force(rows, all_time):
    """Every rule applied to every result, then each athlete's best, then the top 10."""
    today = date.today()
    since = None if all_time else (today.replace(year=today.year - 1) if (today.month, today.day) != (2, 29)
                                   else today.replace(year=today.year - 1, day=28))
    excluded = R._listed(R.EXCLUDED_RESULTS, index.normalize)
    confirmed = R._listed(R.CONFIRMED_RESULTS, index.normalize)
    lo, hi = R.CJ_TO_SNATCH
    by_athlete = {}
    for r in rows:
        by_athlete.setdefault(r["key"], []).append(r)
    best = {"Men": [], "Women": []}
    for key, results in by_athlete.items():
        flags = R.jump_flags(results)
        for gender in ("Men", "Women"):
            eligible = []
            for r, jump in zip(results, flags):
                ident = (r["key"], r["meet_key"], r["date"].isoformat() if r["date"] else None, r["total"])
                if (r["gender"] != gender or r["bodyweight"] < R.MIN_BODYWEIGHT[gender] or ident in excluded
                        or (since and (r["date"] is None or r["date"] < since))):
                    continue
                if r["best_sn"] <= 0 or not lo <= r["best_cj"] / r["best_sn"] <= hi or (jump and ident not in confirmed):
                    continue
                eligible.append({**r, "q_points": R.q_points(r["total"], r["bodyweight"], gender)})
            if eligible:
                best[gender].append(max(eligible, key=lambda r: (r["q_points"], r["date"] or date.min)))
    return {g: [(r["name"], r["meet"], r["date"], round(r["q_points"], 3))
                for r in sorted(b, key=lambda r: (-r["q_points"], r["name"]))[: R.TOP_N]] for g, b in best.items()}


def main():
    rows = index.with_cursor(fetch_all)
    rows = [{**r, "total": float(r["total"]),
             "bodyweight": float(r["bodyweight"]) if r["bodyweight"] is not None else 0.0,
             "best_sn": float(r["best_sn"] or 0), "best_cj": float(r["best_cj"] or 0)} for r in rows]
    print(f"fetched {len(rows):,} real results")

    # every hand-kept entry must match exactly one stored result
    idents = {}
    for r in rows:
        ident = (r["key"], r["meet_key"], r["date"].isoformat() if r["date"] else None, r["total"])
        idents[ident] = idents.get(ident, 0) + 1
    for label, entries in (("excluded", R.EXCLUDED_RESULTS), ("confirmed", R.CONFIRMED_RESULTS)):
        for name, meet, d, total, _ in entries:
            n = idents.get((index.normalize(name), index.normalize(meet), d, float(total)), 0)
            check(f"{label} entry {name} ({meet}, {d}) matches exactly one result", n == 1, f"{n} matches")

    for all_time in (False, True):
        label = "all time" if all_time else "past year"
        expected = brute_force(rows, all_time)
        got = index.with_cursor(lambda cur: R.compute_rankings(
            cur, all_time, index.normalize, index.NAME_KEY_SQL, index.NAME_DISPLAY_SQL))
        for gender in ("Men", "Women"):
            got_rows = [(r["name"], r["meet"], r["date"], round(r["q_points"], 3)) for r in got[gender]]
            check(f"{label}, {gender}: the fast rankings equal the rules applied to every result",
                  got_rows == expected[gender],
                  "" if got_rows == expected[gender] else f"got {got_rows[:3]}... expected {expected[gender][:3]}...")

    print("\n" + (f"{len(failures)} FAILED: {failures}" if failures else "ALL PASSED"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

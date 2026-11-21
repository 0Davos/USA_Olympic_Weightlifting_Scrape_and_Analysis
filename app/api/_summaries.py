"""The home page's whole-table summaries (Q-points lists and distributions, Fastest improvers, athlete
counts), built once per data load and stored in the small `site_cache` table.

Each of these reads all of meet_results and sorts or groups far more than the database's 2 MB of working
memory, so every run spilled to temporary files on disk: about 120 MB per uncached round of the home page,
which used up Supabase's Disk IO budget and took the database down on 2026-11-21. The data only changes
when transform/load_to_supabase.py reloads it, so that script builds every summary here once, in the same
transaction as the reload, and the API just reads the stored copy. If a summary is missing (the table not
created yet, or an older load), the API builds it live as before.

Kept free of FastAPI so the load script can import it with the pipeline's own dependencies.
The leading underscore keeps Vercel from treating this file as an endpoint.
"""

import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal

import psycopg2

import _rankings

CACHE_TABLE = "site_cache"

# Athletes are identified by name only, and the source has spelling noise (stray double
# spaces, inconsistent capitalisation), so every endpoint matches on a normalized key:
# trimmed, whitespace collapsed, lowercased. NAME_DISPLAY_SQL is the same minus the
# lowercasing, used to show a cleaned-up name.
NAME_DISPLAY_SQL = r"regexp_replace(btrim(name), '\s+', ' ', 'g')"
NAME_KEY_SQL = f"lower({NAME_DISPLAY_SQL})"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def to_json_row(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, date):
            value = value.isoformat()
        out[key] = value
    return out


def pick_display_name(rows: list[dict]) -> str:
    """The most common cleaned-up spelling among an athlete's rows (ties: alphabetical)."""
    spellings = Counter(r["name"] for r in rows)
    return sorted(spellings, key=lambda s: (-spellings[s], s))[0]


# ---- the summaries. Each builder takes an open RealDictCursor and returns the endpoint's JSON body.

def build_q_points(cur, window: str) -> dict:
    lists = _rankings.compute_rankings(cur, window == "all", normalize, NAME_KEY_SQL, NAME_DISPLAY_SQL)

    def entry(r: dict) -> dict:
        out = to_json_row(r)
        out["q_points"] = round(out["q_points"], 1)
        return out

    return {"window": window, "men": [entry(r) for r in lists["Men"]], "women": [entry(r) for r in lists["Women"]]}


def build_distribution(cur, window: str) -> dict:
    dist = _rankings.compute_distribution(cur, window == "all", NAME_KEY_SQL)
    return {"window": window, "men": dist["Men"], "women": dist["Women"]}


def build_improvers(cur) -> dict:
    found = _rankings.compute_improvers(cur, normalize, NAME_KEY_SQL, NAME_DISPLAY_SQL)

    def entry(r: dict) -> dict:
        # rounded before subtracting, so the gain shown always equals now minus before as shown
        out = to_json_row(r)
        out["q_points"], out["before_q_points"] = round(out["q_points"], 1), round(out["before_q_points"], 1)
        out["gain"] = round(out["q_points"] - out["before_q_points"], 1)
        return out

    return {"men": [entry(r) for r in found["Men"]], "women": [entry(r) for r in found["Women"]]}


# ---- athlete counts (the two bar charts at the bottom of the home page)

# The USAW records effectively start in 2012: about 150 athletes have a "first meet" before that, on
# impossible dates (1905, 1958, ...), so the new-athletes chart starts here and leaves those out. 2012
# itself also counts everyone who was already competing when the records begin.
STATS_FIRST_YEAR = 2012
# The meets-per-athlete chart has one bar per count up to this; athletes with more are reported as a number.
STATS_MAX_MEETS_BAR = 30


def build_stats(cur) -> dict:
    """New athletes per year (each athlete counted in the year of their first dated meet) and how many
    athletes have attended each number of meets, all time. Athletes are name keys, as everywhere on the
    site; a meet is a distinct (meet, date), bomb-outs included. One pass over the table (about 3s, and
    79 MB of temporary files, when run live), plus an indexed lookup of the most-meets athlete's name."""
    cur.execute(f"""
    WITH athletes AS (
        SELECT {NAME_KEY_SQL} AS key, min(date) AS first,
               count(DISTINCT (lower(regexp_replace(btrim(meet), '\\s+', ' ', 'g')), date)) AS meets
        FROM meet_results
        WHERE date IS NULL OR date <= current_date
        GROUP BY 1
    )
    SELECT 'year' AS kind, extract(year FROM first)::int AS value, count(*) AS athletes, NULL AS name
    FROM athletes WHERE first IS NOT NULL GROUP BY 2
    UNION ALL
    SELECT 'meets', meets::int, count(*), NULL FROM athletes GROUP BY 2
    UNION ALL
    (SELECT 'most', meets::int, 1, key FROM athletes ORDER BY meets DESC, key LIMIT 1)
    """)
    rows = cur.fetchall()
    top = next((r["name"] for r in rows if r["kind"] == "most"), None)
    most_name = None
    if top:
        cur.execute(f"SELECT {NAME_DISPLAY_SQL} AS name FROM meet_results WHERE {NAME_KEY_SQL} = %s", (top,))
        names = cur.fetchall()
        most_name = pick_display_name(names) if names else None

    by_year = {r["value"]: r["athletes"] for r in rows if r["kind"] == "year"}
    by_meets = {r["value"]: r["athletes"] for r in rows if r["kind"] == "meets"}
    more = [m for m in by_meets if m > STATS_MAX_MEETS_BAR]
    return {
        "new_per_year": [{"year": y, "athletes": by_year.get(y, 0)}
                         for y in range(STATS_FIRST_YEAR, date.today().year + 1)],
        "current_year": date.today().year,
        "meets_per_athlete": [{"meets": m, "athletes": by_meets.get(m, 0)}
                              for m in range(1, STATS_MAX_MEETS_BAR + 1)],
        # the athlete with the most meets, linked from the chart
        "more_meets": {"athletes": sum(by_meets[m] for m in more), "most": max(more, default=None),
                       "most_name": most_name},
        "athletes": sum(by_meets.values()),
    }


# Cache key -> builder. The "past year" summaries are as of the day they were built (each data load).
BUILDERS = {
    "q_points_year": lambda cur: build_q_points(cur, "year"),
    "q_points_all": lambda cur: build_q_points(cur, "all"),
    "distribution_year": lambda cur: build_distribution(cur, "year"),
    "distribution_all": lambda cur: build_distribution(cur, "all"),
    "improvers": build_improvers,
    "stats_athletes": build_stats,
}


def read_cached(cur, key: str) -> dict | None:
    """The stored summary, or None if there isn't one (no row yet, or no cache table at all).
    The API's connection is in autocommit mode, so a failed read here doesn't affect later statements."""
    try:
        cur.execute(f'SELECT payload FROM "{CACHE_TABLE}" WHERE key = %s', (key,))
    except (psycopg2.errors.UndefinedTable, psycopg2.errors.InsufficientPrivilege):
        return None
    row = cur.fetchone()
    return row["payload"] if row else None


def refresh_cache(cur) -> list[str]:
    """Builds every summary and replaces the stored copies. Run by the load script, as the table owner,
    inside the reload's transaction so the summaries always match the data. Returns the keys written."""
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{CACHE_TABLE}" (
            key text PRIMARY KEY,
            payload jsonb NOT NULL,
            computed_at timestamptz NOT NULL DEFAULT now()
        )""")
    # Same lockdown as meet_results (db/website_access.sql): Supabase gives new tables full privileges for
    # its public REST roles, so turn row-level security on, revoke them, and let only the website's
    # read-only login select. Each role is only touched if it exists.
    cur.execute(f"""
        DO $$
        BEGIN
            ALTER TABLE "{CACHE_TABLE}" ENABLE ROW LEVEL SECURITY;
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON "{CACHE_TABLE}" FROM anon;
            END IF;
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON "{CACHE_TABLE}" FROM authenticated;
            END IF;
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'website_reader') THEN
                GRANT SELECT ON "{CACHE_TABLE}" TO website_reader;
                DROP POLICY IF EXISTS website_reader_select ON "{CACHE_TABLE}";
                CREATE POLICY website_reader_select ON "{CACHE_TABLE}" FOR SELECT TO website_reader USING (true);
            END IF;
        END
        $$""")
    # Enough working memory for these sorts to stay off the disk, for this transaction only.
    cur.execute("SET LOCAL work_mem = '64MB'")
    payloads = {key: build(cur) for key, build in BUILDERS.items()}
    cur.execute(f'DELETE FROM "{CACHE_TABLE}"')
    for key, payload in payloads.items():
        cur.execute(f'INSERT INTO "{CACHE_TABLE}" (key, payload) VALUES (%s, %s)', (key, json.dumps(payload)))
    return list(payloads)

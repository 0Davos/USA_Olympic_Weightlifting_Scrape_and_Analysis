import logging
import os
import re
from collections import Counter
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from psycopg2.extras import RealDictCursor

try:
    # Local dev only - on Vercel SUPABASE_DB_URL comes from the project's environment variables.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

app = FastAPI()

SEARCH_LIMIT = 10

# Athletes are identified by name only, and the source has spelling noise (stray double
# spaces, inconsistent capitalisation), so both endpoints match on a normalized key:
# trimmed, whitespace collapsed, lowercased. NAME_DISPLAY_SQL is the same minus the
# lowercasing, used to show a cleaned-up name.
NAME_DISPLAY_SQL = r"regexp_replace(btrim(name), '\s+', ' ', 'g')"
NAME_KEY_SQL = f"lower({NAME_DISPLAY_SQL})"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def get_connection():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        logger.error("SUPABASE_DB_URL is not set")
        raise HTTPException(status_code=503, detail="Database not configured")
    # psycopg2 takes a plain postgresql:// URL, not SQLAlchemy's postgresql+driver:// form.
    url = re.sub(r"^postgresql\+\w+://", "postgresql://", url)
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.set_session(readonly=True, autocommit=True)  # this API only ever reads
    return conn


def run_query(sql: str, params: tuple) -> list[dict]:
    # One short-lived connection per request: no pool to manage in a serverless function.
    try:
        with closing(get_connection()) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 5000")
            cur.execute(sql, params)
            return cur.fetchall()
    except psycopg2.Error:
        logger.exception("database query failed")
        raise HTTPException(status_code=503, detail="Database unavailable")


def to_json_row(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, date):
            value = value.isoformat()
        out[key] = value
    return out


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/athletes/search")
def ath_group_find(q: str = Query(..., min_length=1, max_length=100)):
    """Prefix search: up to 10 unique athlete names starting with `q`, alphabetical.
    Case-insensitive and whitespace-insensitive; names that differ only in case/spacing
    come back once, using their most common spelling."""
    key = normalize(q)
    if not key:
        return {"query": q, "names": []}

    # Escape LIKE wildcards so a typed % or _ is matched literally.
    pattern = re.sub(r"([\\%_])", r"\\\1", key) + "%"

    rows = run_query(
        f"""
        SELECT display FROM (
            SELECT DISTINCT ON (key) key, display FROM (
                SELECT {NAME_KEY_SQL} AS key, {NAME_DISPLAY_SQL} AS display, count(*) AS n
                FROM meet_results
                WHERE {NAME_KEY_SQL} LIKE %s
                GROUP BY 1, 2
            ) spellings
            ORDER BY key, n DESC, display
        ) one_per_key
        ORDER BY key
        LIMIT %s
        """,
        (pattern, SEARCH_LIMIT),
    )
    return {"query": q, "names": [r["display"] for r in rows]}


@app.get("/api/athletes/history")
def ath_indv_find(name: str = Query(..., min_length=1, max_length=150)):
    """Full meet history for one athlete, oldest first (meets with an unknown date last).
    Athletes are grouped by name only, so two different people sharing a name are merged.
    Missed attempts come back as null; bomb-outs are included with bombed_out=true."""
    key = normalize(name)
    rows = run_query(
        f"""
        SELECT {NAME_DISPLAY_SQL} AS name, meet, date, weight_category, bodyweight,
               sn_1, sn_2, sn_3, cj_1, cj_2, cj_3, best_sn, best_cj, total,
               age_group, gender, weight_class, bombed_out
        FROM meet_results
        WHERE {NAME_KEY_SQL} = %s
        ORDER BY date ASC NULLS LAST, meet, id
        """,
        (key,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Athlete not found")

    spellings = Counter(r["name"] for r in rows)
    display_name = sorted(spellings, key=lambda s: (-spellings[s], s))[0]
    results = [to_json_row({k: v for k, v in r.items() if k != "name"}) for r in rows]
    return {"name": display_name, "count": len(results), "results": results}

"""Q-points rankings for the home page: each gender's top 10 athletes, by their best result.

Q-points (Marianne Huebner's formula) scores a total relative to bodyweight on one scale for men and
women. No age factor is applied: the source data has age divisions but no exact ages (see ROADMAP.md).
Computed in SQL at request time from meet_results, so no extra table or pipeline step is needed; the
API caches the response (see index.py), since the data only changes when the weekly reload runs.

The leading underscore keeps Vercel from treating this file as an endpoint.
"""

# Q-points constants: score = total * NUMERATOR / (A - B * x^-2 + C * x^2), with x = bodyweight / 100.
Q_POINTS = {
    "Men": {"numerator": 463.26, "a": 416.7, "b": 47.87, "c": 18.93},
    "Women": {"numerator": 306.54, "a": 266.5, "b": 19.44, "c": 18.61},
}

# The formula is fitted to adult lifters and breaks down for very light bodyweights (it's undefined
# below about 34 kg for men and 27 kg for women, and multiplies totals enormously just above that), so
# results lighter than the lightest senior classes aren't ranked.
MIN_BODYWEIGHT = {"Men": 55.0, "Women": 45.0}

# Results whose clean & jerk is outside this multiple of the snatch are almost always data-entry errors
# (e.g. a 21 kg snatch with a 223 kg clean & jerk). 99.8% of real results fall between 0.99 and 1.81.
CJ_TO_SNATCH = (0.9, 1.8)

# A total more than JUMP_RATIO times the athlete's best total at any OTHER meet (before or after) is
# almost always someone else's result filed under their name - provided they competed within
# JUMP_MAX_GAP_DAYS of it, since a genuine jump that size takes time. Tested 2026-11-08 on all 304K real
# results: it flags 0.15% of them and caught 6 of the 7 suspicious all-time women's results the user
# reviewed, while leaving the past-year lists untouched.
JUMP_RATIO = 1.4
JUMP_MAX_GAP_DAYS = 730

# Hand-kept lists, reviewed with the user 2026-11-08 (each list's top 30). Matched on the athlete's name
# key and the meet name (both trimmed, whitespace collapsed, lowercased), the date and the total (a lifter
# can have two entries at one meet). Entries are (name, meet, "YYYY-MM-DD", total, reason).
#
# EXCLUDED_RESULTS never count: wrong division, impossible for the age group, test entries, or errors the
# automatic rules above can't see.
EXCLUDED_RESULTS: list[tuple[str, str, str, float, str]] = [
    ("Ansley Amore", "Tampa Bay Spring Classic", "2018-04-15", 295,
     "295 at 93.8kg the day after an 82 at 81.9kg; her other 53 meets top out at 195"),
    ("Lynn Woodall", "Aurora Weightlifting Open Spring Slam", "2017-05-06", 289,
     "289; her other 12 meets are all 124-138"),
    ("Andrea Martin", "2019 Sooner State Open", "2019-11-02", 290,
     "290 at 135kg; same meet and day she also has her real 62 at 63.1kg"),
    ("Becky Glass", "Barbell Madness II", "2016-03-12", 299,
     "299 in Masters 65-69, only meet; far beyond any woman that age"),
    ("Jean Holloway", "ASQW Jingle Brews Classic", "2018-12-29", 290,
     "290 in Masters 70-74, only meet; far beyond any woman that age"),
    ("Donna Johnson", "The Praelium", "2018-09-02", 285,
     "285 in Masters 70-74, only meet; far beyond any woman that age"),
    ("I-Esha Scott", "NOVA Open", "2016-10-01", 271,
     "271 at 84.6kg; her only other meet was a 120, nearly 3 years earlier (too far apart for the jump rule)"),
    ("Lauren Gilbert", "Inland Empire Classic II", "2019-09-21", 253,
     "253 at 71.8kg, her only meet ever, near the US record at the time; nothing found online to support it"),
]

# CONFIRMED_RESULTS are known to be real, so the jump rule never drops them (the other rules still apply).
# Also confirmed real by the user, though no rule catches them today: Travis Cooper and Daniel Dodd
# (Men's Masters 35-39).
CONFIRMED_RESULTS: list[tuple[str, str, str, float, str]] = [
    ("Ulugbek Alimov", "5 th ASIAN INDOOR MARTIAL ARTS GAMES WEIGHTLIFTING", "2017-09-25", 364,
     "international meet; 1.44x his best US result (252), so the jump rule would otherwise drop it"),
]


TOP_N = 10
# Athletes per gender fetched as candidates before the jump rule is applied (see compute_rankings).
CANDIDATES = 40

MEET_KEY_SQL = r"lower(regexp_replace(btrim(r.meet), '\s+', ' ', 'g'))"


def q_points(total: float, bodyweight: float, gender: str) -> float:
    """The formula in Python (the user's original code, without its age factor). The SQL below computes
    the same thing; the checks confirm they agree."""
    k = Q_POINTS[gender]
    x = bodyweight / 100
    return total * k["numerator"] / (k["a"] - k["b"] * x**-2 + k["c"] * x**2)


def _q_points_sql() -> str:
    def expr(gender: str) -> str:
        k = Q_POINTS[gender]
        return (f"{k['numerator']} / ({k['a']} - {k['b']} * power(r.bodyweight / 100.0, -2)"
                f" + {k['c']} * power(r.bodyweight / 100.0, 2))")

    return f"r.total * CASE WHEN r.gender = 'Women' THEN {expr('Women')} ELSE {expr('Men')} END"


def candidates_query(name_key_sql: str) -> str:
    """Each gender's top %(limit)s athletes by best Q-points under the rules that need only the result
    itself (gender, bodyweight floor, snatch/clean & jerk ratio, date window). The jump rule (which needs
    each athlete's whole history) and the hand-kept lists are applied afterwards, in compute_rankings: both
    only ever lower an athlete's best, so these candidates' scores are upper bounds. Parameters: all_time,
    limit."""
    lo, hi = CJ_TO_SNATCH
    return f"""
        WITH best AS (
            SELECT r.gender, {name_key_sql} AS key, max({_q_points_sql()}) AS best
            FROM meet_results r
            WHERE r.gender IN ('Men', 'Women') AND NOT r.bombed_out AND r.total > 0
              AND r.bodyweight >= CASE WHEN r.gender = 'Women' THEN {MIN_BODYWEIGHT['Women']} ELSE {MIN_BODYWEIGHT['Men']} END
              AND r.best_sn > 0 AND r.best_cj / r.best_sn BETWEEN {lo} AND {hi}
              AND (%(all_time)s OR r.date >= current_date - interval '1 year')
            GROUP BY 1, 2
        ), ranked AS (
            SELECT *, row_number() OVER (PARTITION BY gender ORDER BY best DESC) AS rank FROM best
        )
        SELECT gender, key, best FROM ranked WHERE rank <= %(limit)s
    """


def history_query(name_key_sql: str, name_display_sql: str) -> str:
    """Every real result (any gender, any date) of the athletes in %(keys)s: the jump rule compares each
    result with the athlete's others. Uses the name-key index (db/indexes.sql)."""
    return f"""
        SELECT {name_key_sql} AS key, {name_display_sql} AS name, r.gender, r.meet, {MEET_KEY_SQL} AS meet_key,
               r.date, r.bodyweight, r.total, r.best_sn, r.best_cj
        FROM meet_results r
        WHERE {name_key_sql} = ANY(%(keys)s) AND NOT r.bombed_out AND r.total > 0
    """


def _listed(entries, normalize) -> set:
    """A hand-kept list as a set of (name key, meet key, "YYYY-MM-DD", total), the same keys as the SQL's."""
    return {(normalize(name), normalize(meet), d, float(total)) for name, meet, d, total, _ in entries}


def jump_flags(results: list[dict]) -> list[bool]:
    """For one athlete's real results: is each total more than JUMP_RATIO times their best total at any
    other meet, with another meet within JUMP_MAX_GAP_DAYS? (An undated result is never flagged.)"""
    flags = []
    for i, r in enumerate(results):
        others = [o for j, o in enumerate(results) if j != i]
        if not others or r["date"] is None:
            flags.append(False)
            continue
        best_elsewhere = max(o["total"] for o in others)
        gaps = [abs((o["date"] - r["date"]).days) for o in others if o["date"] is not None]
        flags.append(r["total"] > JUMP_RATIO * best_elsewhere and bool(gaps) and min(gaps) <= JUMP_MAX_GAP_DAYS)
    return flags


def compute_rankings(cur, all_time: bool, normalize, name_key_sql: str, name_display_sql: str) -> dict:
    """{"Men": [...], "Women": [...]}, each the top TOP_N athletes (rank, name, meet, date, bodyweight,
    total, q_points), on an open database cursor.

    Two fast queries instead of one slow one (checking every result's history in SQL took 5-7s): the
    CANDIDATES best athletes per gender under the per-result rules, then those athletes' full histories,
    on which the jump rule and the hand-kept lists are applied here. That gives the same answer as
    applying them to everyone, as long as the top TOP_N afterwards still score above the best athlete left
    outside the candidates - checked below, widening the pool if not."""
    from datetime import date as _date

    excluded, confirmed = _listed(EXCLUDED_RESULTS, normalize), _listed(CONFIRMED_RESULTS, normalize)
    today = _date.today()
    # Same cutoff as the SQL's current_date - interval '1 year' (29 February maps to 28 February).
    since = None if all_time else (today.replace(year=today.year - 1) if (today.month, today.day) != (2, 29)
                                   else today.replace(year=today.year - 1, day=28))
    lo, hi = CJ_TO_SNATCH
    limit = CANDIDATES
    while True:
        # limit + 1: the extra athlete is the best one left outside the pool, for the check below
        cur.execute(candidates_query(name_key_sql), {"all_time": all_time, "limit": limit + 1})
        cands = cur.fetchall()
        cur.execute(history_query(name_key_sql, name_display_sql), {"keys": sorted({c["key"] for c in cands})})
        history = {}
        for row in cur.fetchall():
            row = {**row, "total": float(row["total"]),
                   "bodyweight": float(row["bodyweight"]) if row["bodyweight"] is not None else 0.0,
                   "best_sn": float(row["best_sn"] or 0), "best_cj": float(row["best_cj"] or 0)}
            history.setdefault(row["key"], []).append(row)

        out, complete = {}, True
        for gender in ("Men", "Women"):
            gcands = sorted((c for c in cands if c["gender"] == gender), key=lambda c: -float(c["best"]))
            inside, outside = gcands[:limit], gcands[limit:]
            best_rows = []
            for c in inside:
                results = history.get(c["key"], [])
                eligible = []
                for r, jump in zip(results, jump_flags(results)):
                    ident = (r["key"], r["meet_key"], r["date"].isoformat() if r["date"] else None, r["total"])
                    if (r["gender"] != gender or r["bodyweight"] < MIN_BODYWEIGHT[gender] or ident in excluded
                            or (since and (r["date"] is None or r["date"] < since))):
                        continue
                    if r["best_sn"] <= 0 or not lo <= r["best_cj"] / r["best_sn"] <= hi or (jump and ident not in confirmed):
                        continue
                    eligible.append({**r, "q_points": q_points(r["total"], r["bodyweight"], gender)})
                if eligible:  # their best result (latest one on a tie)
                    best_rows.append(max(eligible, key=lambda r: (r["q_points"], r["date"] or _date.min)))
            best_rows.sort(key=lambda r: (-r["q_points"], r["name"]))
            top = best_rows[:TOP_N]
            # Exact only if the TOP_N-th still beats everyone outside the candidate pool.
            if outside and (len(top) < TOP_N or top[-1]["q_points"] < float(outside[0]["best"])):
                complete = False
            out[gender] = [
                {"rank": i + 1, "name": r["name"], "meet": r["meet"], "date": r["date"],
                 "bodyweight": r["bodyweight"], "total": r["total"], "q_points": r["q_points"]}
                for i, r in enumerate(top)
            ]
        if complete:
            return out
        limit *= 2

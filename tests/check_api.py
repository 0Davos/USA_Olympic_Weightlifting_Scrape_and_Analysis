"""Checks for the website's API (app/api/index.py) against the live Supabase table.

Calls the endpoints in-process through FastAPI's test client, so no server needs to be running.
Test athletes are found by querying the table (a normal one, one with a bomb-out, one with only an
undated meet, one whose name has spelling variants), and expected counts come straight from SQL, so
the checks keep working as new meets are scraped.

Needs SUPABASE_DB_URL in the repo-root .env and network access. Read-only: the API only ever reads.
Run from the repo root:  python tests/check_api.py
"""

import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
import index  # noqa: E402  (also loads the repo-root .env)

client = TestClient(index.app)
failures = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def get(url, **params):
    """GET, retrying a couple of times on 503 (a dropped network connection is not what's under test)."""
    for _ in range(3):
        r = client.get(url, params=params)
        if r.status_code != 503:
            return r
        time.sleep(2)
    return r


def sql(query, params=()):
    for _ in range(3):
        try:
            return index.run_query(query, params)
        except Exception:
            time.sleep(2)
    raise SystemExit("could not reach the database - check SUPABASE_DB_URL and your network")


def first(query, params=()):
    rows = sql(query, params)
    return next(iter(rows[0].values())) if rows else None


# ---- find test athletes in the data
KEY = index.NAME_KEY_SQL
normal = first(f"""SELECT name FROM meet_results WHERE date IS NOT NULL GROUP BY name
                   HAVING count(*) BETWEEN 4 AND 10 AND max(date) <= current_date AND bool_and(NOT bombed_out)
                   ORDER BY name LIMIT 1""")
# an athlete with a bomb-out AND a completed total (the models predict a change from the last one)
bomber = first(f"""SELECT min(name) FROM meet_results WHERE date IS NOT NULL GROUP BY {KEY}
                   HAVING bool_or(bombed_out) AND bool_or(NOT bombed_out) ORDER BY min(name) LIMIT 1""")
only_bombs = first(f"""SELECT min(name) FROM meet_results WHERE date IS NOT NULL GROUP BY {KEY}
                       HAVING bool_and(bombed_out) ORDER BY min(name) LIMIT 1""")
undated_only = first("SELECT name FROM meet_results GROUP BY name HAVING bool_and(date IS NULL) ORDER BY name LIMIT 1")
variants = sql(f"""SELECT array_agg(DISTINCT name) AS names FROM (SELECT {KEY} AS key, name FROM meet_results) t
                   GROUP BY key HAVING count(DISTINCT name) > 1 ORDER BY key LIMIT 1""")
variants = variants[0]["names"] if variants else None
print(f"test athletes: normal={normal!r} bomb-out={bomber!r} undated-only={undated_only!r} spelling-variants={variants}\n")
assert normal and bomber, "the table doesn't have the athletes these checks need"

today = date.today()
cap = today + timedelta(days=365)


def count_for(name):
    return first(f"SELECT count(*) FROM meet_results WHERE {KEY} = %s", (index.normalize(name),))


# ================= health, and laziness of the prediction import
r = get("/api/health")
check("health", r.status_code == 200 and r.json() == {"status": "ok"})

# ================= search
q = index.normalize(normal)
r = get("/api/athletes/search", q=q)
names = r.json().get("names", [])
check("search by a full name finds that athlete", r.status_code == 200 and any(index.normalize(n) == q for n in names), str(names[:3]))
r = get("/api/athletes/search", q=q[:5])
names = r.json()["names"]
check("search returns at most 10, alphabetical", len(names) <= 10 and names == sorted(names, key=str.lower))
check("every result starts with the query (ignoring case and spacing)", all(index.normalize(n).startswith(q[:5]) for n in names))
check("search ignores case and extra spaces", get("/api/athletes/search", q="  " + q[:5].upper() + "  ").json()["names"] == names)
r = get("/api/athletes/search", q="a")
check("a single letter returns 10 distinct names", len(r.json()["names"]) == 10 and len({index.normalize(n) for n in r.json()["names"]}) == 10)
for bad, label in [("%", "'%'"), ("_", "'_'")]:
    r = get("/api/athletes/search", q=bad)
    check(f"{label} is matched literally, not as a wildcard", r.status_code == 200 and r.json()["names"] == [])
check("whitespace-only query -> empty list", get("/api/athletes/search", q="   ").json()["names"] == [])
check("empty q -> 422", get("/api/athletes/search", q="").status_code == 422)
check("missing q -> 422", get("/api/athletes/search").status_code == 422)
check("101-character q -> 422", get("/api/athletes/search", q="x" * 101).status_code == 422)
r = get("/api/athletes/search", q="'; drop table meet_results; --")
check("SQL-injection-looking query is just no match", r.status_code == 200 and r.json()["names"] == [])
if variants:
    key = index.normalize(variants[0])
    shown = [n for n in get("/api/athletes/search", q=key).json()["names"] if index.normalize(n) == key]
    check("spelling variants appear once in search", len(shown) == 1, str(shown))

# ================= history
r = get("/api/athletes/history", name=normal)
j = r.json()
check("history 200", r.status_code == 200)
res = j["results"]
check("history count matches the database", j["count"] == len(res) == count_for(normal), f"{j['count']} vs {count_for(normal)}")
dated = [x["date"] for x in res if x["date"]]
check("history is oldest first", dated == sorted(dated))
want = {"meet", "date", "weight_category", "bodyweight", "sn_1", "sn_2", "sn_3", "cj_1", "cj_2", "cj_3",
        "best_sn", "best_cj", "total", "age_group", "gender", "weight_class", "bombed_out"}
check("history rows have exactly the documented fields", set(res[0]) == want, str(set(res[0]) ^ want))
check("numbers come back as JSON numbers", isinstance(res[0]["total"], float) and isinstance(res[0]["bodyweight"], float))
check("display name has no double spaces", "  " not in j["name"], j["name"])
check("history lookup ignores case and spacing", get("/api/athletes/history", name="  " + normal.upper() + " ").json()["count"] == j["count"])
check("unknown athlete -> 404", get("/api/athletes/history", name="Definitely Not An Athlete").status_code == 404)
check("missing name -> 422", get("/api/athletes/history").status_code == 422)
if variants:
    counts = [get("/api/athletes/history", name=v).json()["count"] for v in variants]
    check("every spelling variant resolves to the same history", len(set(counts)) == 1 and counts[0] == count_for(variants[0]), f"{variants} -> {counts}")
b = get("/api/athletes/history", name=bomber).json()["results"]
check("bomb-outs are returned, flagged, with a total of 0", any(x["bombed_out"] and x["total"] == 0.0 for x in b))
if undated_only:
    u = get("/api/athletes/history", name=undated_only).json()["results"]
    check("undated meets come back with a null date", len(u) >= 1 and all(x["date"] is None for x in u))

check("search and history did NOT load the prediction module (its import is lazy)", "_prediction" not in sys.modules)

# ================= predict
def latest_of(name):
    ds = [x["date"] for x in get("/api/athletes/history", name=name).json()["results"] if x["date"]]
    return date.fromisoformat(max(ds))


def predict(name, target, bodyweight=80):
    return get("/api/athletes/predict", name=name, date=target.isoformat(), bodyweight=bodyweight)


latest = latest_of(normal)
target = max(today, latest) + timedelta(days=60)
r = predict(normal, target)
j = r.json()
check("predict 200", r.status_code == 200, r.text[:120])
check("prediction module loaded lazily on the first prediction", "_prediction" in sys.modules)
check("predicting never imports the lightgbm package (it can't load on Vercel)", "lightgbm" not in sys.modules)
p = j["prediction"]
check("response has exactly the documented fields", set(j) == {"name", "date", "bodyweight", "latest_meet", "prediction", "meets_used", "assumes_no_bomb_out"})
check("all five percentiles returned (q1 ... q99)", list(p) == ["q1", "q25", "q50", "q75", "q99"], str(list(p)))
check("percentiles ordered q1 <= q25 <= ... <= q99", list(p.values()) == sorted(p.values()), str(p))
hist = get("/api/athletes/history", name=normal).json()["results"]
real_last = [x for x in hist if x["date"]][-1]
check("latest_meet is the athlete's real latest meet", j["latest_meet"] == {"date": real_last["date"], "total": real_last["total"], "bombed_out": real_last["bombed_out"]}, str(j["latest_meet"]))
check("meets_used counts the dated meets", j["meets_used"] == sum(1 for x in hist if x["date"]))
check("median is in a plausible range around the last total", 0.6 * real_last["total"] <= p["q50"] <= 1.4 * real_last["total"], f"{p['q50']} vs last {real_last['total']}")
check("assumes_no_bomb_out is set", j["assumes_no_bomb_out"] is True)

r = predict(normal, latest)
check("a date equal to the latest meet -> 422 naming that date", r.status_code == 422 and latest.isoformat() in r.json()["detail"], r.json().get("detail", ""))
check("a date before the latest meet -> 422", predict(normal, latest - timedelta(days=30)).status_code == 422)
r = predict(normal, cap + timedelta(days=1))
check("one day past the 12-month limit -> 422 saying so", r.status_code == 422 and "12 months" in r.json()["detail"] and cap.isoformat() in r.json()["detail"], r.json().get("detail", ""))
check("exactly on the limit is allowed", predict(normal, cap).status_code == 200)
check("bodyweight 0 -> 422", predict(normal, target, 0).status_code == 422)
check("bodyweight 300 -> 422", predict(normal, target, 300).status_code == 422)
check("bodyweight 0.1 (the lower limit) is accepted", predict(normal, target, 0.1).status_code == 200)
check("malformed date -> 422", get("/api/athletes/predict", name=normal, date="not-a-date", bodyweight=80).status_code == 422)
check("missing bodyweight -> 422", get("/api/athletes/predict", name=normal, date=target.isoformat()).status_code == 422)
check("missing name -> 422", get("/api/athletes/predict", date=target.isoformat(), bodyweight=80).status_code == 422)
check("unknown athlete -> 404", predict("Definitely Not An Athlete", target).status_code == 404)
check("SQL-injection-looking name is just not found", predict("x' OR '1'='1", target).status_code == 404)
if undated_only:
    r = predict(undated_only, today + timedelta(days=30))
    check("an athlete with only undated meets -> 422 with a clear reason", r.status_code == 422 and "no dated meets" in r.json()["detail"], r.json().get("detail", ""))
if only_bombs:
    r = predict(only_bombs, max(today, latest_of(only_bombs)) + timedelta(days=30))
    check("an athlete whose every meet was a bomb-out -> 422 (no total to predict a change from)",
          r.status_code == 422 and "no completed total" in r.json()["detail"], r.json().get("detail", ""))
r = predict(bomber, max(today, latest_of(bomber)) + timedelta(days=60))
check("an athlete with bomb-outs in their history can be predicted", r.status_code == 200, r.text[:120])
if variants:
    a, b2 = (predict(v, max(today, latest_of(v)) + timedelta(days=60)) for v in variants[:2])
    check("spelling variants give identical predictions", a.status_code == 200 and a.json()["prediction"] == b2.json()["prediction"])

# ================= Q-points rankings (home page top 10s)
import _rankings  # noqa: E402

ranked = {}
for w in ("year", "all"):
    r = get("/api/rankings/q-points", window=w)
    ranked[w] = r.json() if r.status_code == 200 else None
    check(f"rankings ({w}): 200, with a CDN cache header", r.status_code == 200 and "s-maxage" in r.headers.get("cache-control", ""), str(r.status_code))
    if ranked[w] is None:
        continue
    for g, gender in (("men", "Men"), ("women", "Women")):
        rows = ranked[w][g]
        scores = [x["q_points"] for x in rows]
        check(f"rankings ({w}, {g}): 10 rows ranked 1-10, best first",
              [x["rank"] for x in rows] == list(range(1, 11)) and scores == sorted(scores, reverse=True), str(scores))
        check(f"rankings ({w}, {g}): one row per athlete", len({index.normalize(x["name"]) for x in rows}) == len(rows))
        check(f"rankings ({w}, {g}): Q-points match the Python formula",
              all(abs(_rankings.q_points(x["total"], x["bodyweight"], gender) - x["q_points"]) <= 0.051 for x in rows))
        check(f"rankings ({w}, {g}): nothing below the bodyweight floor",
              all(x["bodyweight"] >= _rankings.MIN_BODYWEIGHT[gender] for x in rows))
cutoff = (today - timedelta(days=366)).isoformat()
if ranked["year"]:
    check("rankings (year): every result is from the past year",
          all(x["date"] and x["date"] >= cutoff for g in ("men", "women") for x in ranked["year"][g]))
if ranked["year"] and ranked["all"]:
    check("rankings: the all-time leaders score at least as high as the past year's",
          all(ranked["all"][g][0]["q_points"] >= ranked["year"][g][0]["q_points"] for g in ("men", "women")))
    # Excluding the all-time women's leader's result by hand must drop it from the list.
    lead = ranked["all"]["women"][0]
    saved_excluded = _rankings.EXCLUDED_RESULTS
    _rankings.EXCLUDED_RESULTS = [(lead["name"], lead["meet"], lead["date"], lead["total"], "check")]
    r = get("/api/rankings/q-points", window="all")
    _rankings.EXCLUDED_RESULTS = saved_excluded
    after = r.json()["women"] if r.status_code == 200 else []
    check("rankings: a result on the exclusion list drops out",
          bool(after) and not any(x["name"] == lead["name"] and x["meet"] == lead["meet"] and x["date"] == lead["date"] for x in after),
          f"{lead['name']} at {lead['meet']}")
r = client.get("/api/rankings/q-points", params={"window": "month"})
check("rankings: an unknown window -> 422", r.status_code == 422)

# ================= Q-points distribution (the charts under the top 10s)
dist = {}
for w in ("year", "all"):
    r = get("/api/rankings/q-points/distribution", window=w)
    dist[w] = r.json() if r.status_code == 200 else None
    check(f"distribution ({w}): 200, with a CDN cache header", r.status_code == 200 and "s-maxage" in r.headers.get("cache-control", ""), str(r.status_code))
    if dist[w] is None:
        continue
    for g in ("men", "women"):
        d = dist[w][g]
        los = [b["lo"] for b in d["bins"]]
        cuts = [p["q_points"] for p in d["percentiles"]]
        check(f"distribution ({w}, {g}): the bins add up to the athlete count",
              d["athletes"] > 0 and sum(b["athletes"] for b in d["bins"]) == d["athletes"], f"{d['athletes']:,} athletes")
        check(f"distribution ({w}, {g}): bins are contiguous, {d['bin_width']} Q-points wide",
              los == list(range(los[0], los[-1] + d["bin_width"], d["bin_width"])))
        check(f"distribution ({w}, {g}): 25th/50th/75th/90th/99th cutoffs, rising, inside the range",
              [p["p"] for p in d["percentiles"]] == [25, 50, 75, 90, 99] and cuts == sorted(cuts)
              and los[0] <= cuts[0] and cuts[-1] <= los[-1] + d["bin_width"], str(cuts))
        if ranked.get(w):
            check(f"distribution ({w}, {g}): the top 10's best score sits at the top of the range",
                  ranked[w][g][0]["q_points"] <= los[-1] + d["bin_width"])
if dist["year"] and dist["all"]:
    check("distribution: all time covers more athletes than the past year",
          all(dist["all"][g]["athletes"] > dist["year"][g]["athletes"] for g in ("men", "women")))
r = client.get("/api/rankings/q-points/distribution", params={"window": "month"})
check("distribution: an unknown window -> 422", r.status_code == 422)

# ================= caching: successful reads may be reused for an hour, errors never
for label, url, params in (
    ("search", "/api/athletes/search", {"q": "a"}),
    ("history", "/api/athletes/history", {"name": normal}),
    ("rankings", "/api/rankings/q-points", {"window": "year"}),
    ("distribution", "/api/rankings/q-points/distribution", {"window": "year"}),
):
    r = get(url, **params)
    cc = r.headers.get("cache-control", "")
    check(f"caching: {label} may be reused for an hour by browsers and the CDN",
          r.status_code == 200 and "max-age=3600" in cc and "s-maxage=3600" in cc and "public" in cc, cc)
r = client.get("/api/athletes/history", params={"name": "Definitely Not An Athlete"})
check("caching: a 404 is never cached", r.status_code == 404 and "max-age" not in r.headers.get("cache-control", ""),
      r.headers.get("cache-control", "(none)"))

# ================= failure handling: always a clean 503, never a stack trace or a leak
saved = os.environ.get("SUPABASE_DB_URL")
os.environ["SUPABASE_DB_URL"] = "postgresql://nobody:wrong@127.0.0.1:1/postgres"
r = client.get("/api/athletes/search", params={"q": "a"})
check("unreachable database -> 503 with a generic message", r.status_code == 503 and r.json() == {"detail": "Database unavailable"}, r.text[:80])
del os.environ["SUPABASE_DB_URL"]
r = client.get("/api/athletes/search", params={"q": "a"})
check("missing SUPABASE_DB_URL -> 503", r.status_code == 503 and r.json() == {"detail": "Database not configured"}, r.text[:80])
if saved:
    os.environ["SUPABASE_DB_URL"] = saved

import _prediction  # noqa: E402

saved_models = (_prediction.MODELS_DIR, _prediction._boosters)
_prediction._boosters = None
_prediction.MODELS_DIR = _prediction.MODELS_DIR.parent / "_missing_models"
r = client.get("/api/athletes/predict", params={"name": normal, "date": target.isoformat(), "bodyweight": 80})
check("missing model files -> generic 503", r.status_code == 503 and r.json() == {"detail": "Prediction unavailable"}, r.text[:80])
_prediction.MODELS_DIR, _prediction._boosters = saved_models

try:
    index.get_connection().cursor().execute("CREATE TEMP TABLE should_fail(x int)")
    check("the API's connection is read-only", False, "a write succeeded")
except Exception as e:
    check("the API's connection is read-only (a write is rejected)", "read-only" in str(e).lower(), str(e).splitlines()[0][:70])

print("\n" + (f"{len(failures)} FAILED: {failures}" if failures else "ALL PASSED"))
sys.exit(1 if failures else 0)

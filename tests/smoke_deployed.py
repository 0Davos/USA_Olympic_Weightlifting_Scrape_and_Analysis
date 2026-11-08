"""Smoke test for a running copy of the website - a Vercel preview or production URL, or the local dev
servers. Checks the whole chain over real HTTP: the pages, the API routing, the database, and a prediction.
Uses only the standard library, so it runs anywhere.

Usage:
    python tests/smoke_deployed.py https://your-preview-url.vercel.app
    python tests/smoke_deployed.py http://localhost:3000            # local: needs both dev servers running

Exit code 0 if everything passes. The first request to a cold server can take many seconds, so each
request is allowed 90s; timings are printed so a slow cold start is visible.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
BASE = sys.argv[1].rstrip("/")
failures = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def fetch(path, **params):
    """GET -> (status, parsed JSON or text, seconds). Non-2xx responses are returned, not raised."""
    url = BASE + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    started = time.time()
    for attempt in (1, 2):  # one retry on a connection failure: a server that's still starting, or DNS right after a deploy
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                status, body = r.status, r.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read().decode("utf-8", "replace")
            break
        except Exception as e:  # DNS failure, timeout, connection refused...
            if attempt == 2:
                return None, f"{type(e).__name__}: {e}", time.time() - started
            time.sleep(4)
    try:
        body = json.loads(body)
    except ValueError:
        pass
    return status, body, time.time() - started


print(f"smoke-testing {BASE}\n")

# ---- pages
for path in ("/", "/about", "/privacy"):
    status, body, secs = fetch(path)
    check(f"page {path} loads", status == 200, f"{status}, {secs:.1f}s" + (f", {body}" if status is None else ""))
status, body, _ = fetch("/this-page-does-not-exist")
check("a nonexistent page returns 404", status == 404, str(status))

# ---- API routing and database
status, body, secs = fetch("/api/health")
check("/api/health reaches the Python API", status == 200 and body == {"status": "ok"}, f"{status}, {secs:.1f}s")

status, body, secs = fetch("/api/athletes/search", q="a")
names = body.get("names", []) if isinstance(body, dict) else []
check("search returns 10 names (so the database is reachable)", status == 200 and len(names) == 10, f"{status}, {secs:.1f}s, first: {names[:2]}")
if not names:
    print("\nCannot continue without a search result - is the API / database reachable at this URL?")
    sys.exit(1)

name = names[0]
status, body, secs = fetch("/api/athletes/history", name=name)
results = body.get("results", []) if isinstance(body, dict) else []
check(f"history for {name!r} loads", status == 200 and len(results) >= 1, f"{status}, {len(results)} meets, {secs:.1f}s")
check("an unknown athlete returns 404", fetch("/api/athletes/history", name="Definitely Not An Athlete")[0] == 404)

# ---- prediction (loads the models on a cold server, so this is the slowest request)
dated = [r["date"] for r in results if r.get("date")]
if dated:
    latest = date.fromisoformat(max(dated))
    target = max(date.today(), latest) + timedelta(days=60)
    status, body, secs = fetch("/api/athletes/predict", name=name, date=target.isoformat(), bodyweight=80)
    p = body.get("prediction", {}) if isinstance(body, dict) else {}
    ordered = bool(p) and all(k in p for k in ("q1", "q25", "q50", "q75", "q99")) and list(p.values()) == sorted(p.values())
    check(f"prediction for {name!r} works, with ordered bands", status == 200 and ordered, f"{status}, {secs:.1f}s, {p}")
    status, body, _ = fetch("/api/athletes/predict", name=name, date=(date.today() + timedelta(days=400)).isoformat(), bodyweight=80)
    check("a date more than 12 months away is rejected with a message", status == 422 and "12 months" in str(body), str(status))
else:
    print("note: that athlete has no dated meets, so the prediction checks were skipped")

# ---- home page Q-points rankings
for window in ("year", "all"):
    status, body, secs = fetch("/api/rankings/q-points", window=window)
    lists = (body.get("men", []), body.get("women", [])) if isinstance(body, dict) else ([], [])
    check(f"Q-points rankings ({window}) return 10 men and 10 women", status == 200 and all(len(x) == 10 for x in lists),
          f"{status}, {secs:.1f}s, leaders: {[x[0]['name'] for x in lists if x]}")

# ---- one athlete page rendered through the website (the browser flow)
status, body, secs = fetch("/athlete/" + urllib.parse.quote(name))
check("the athlete page itself loads", status == 200, f"{status}, {secs:.1f}s")

print("\n" + (f"{len(failures)} FAILED: {failures}" if failures else "ALL PASSED"))
sys.exit(1 if failures else 0)

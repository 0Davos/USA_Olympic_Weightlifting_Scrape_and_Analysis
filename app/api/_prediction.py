"""Predict an athlete's total at a future meet.

Rebuilds the 24 features the quantile models were trained on from the athlete's previous meets
plus the chosen meet date and bodyweight, in plain Python (no pandas: it would push the
deployed function over Vercel's size limit). Every feature mirrors transform/feature_engineering.py
exactly, quirks included; tests/check_prediction_features.py proves that against the real data.
If you change one side, change the other and re-run that check.

The leading underscore keeps Vercel from treating this file (or _models/) as an endpoint.
"""

import math
from datetime import date, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np

# Must equal FEATURE_COLS in models/train.py: the models take features positionally, by index.
# (app/ is all that gets deployed, so this can't be imported from models/; the check script asserts they match.)
FEATURE_COLS = [
    'Bodyweight',
    'athlete_avg_Sn#1_missed', 'athlete_avg_Sn#2_missed', 'athlete_avg_Sn#3_missed',
    'athlete_avg_CJ#1_missed', 'athlete_avg_CJ#2_missed', 'athlete_avg_CJ#3_missed',
    'best_snatch_to_date', 'best_cj_to_date',
    'best_total_to_date', 'Num Competitions', 'Days Since Last Comp',
    'Last Comp Total', 'Days Since Best Total',
    'Gender Binary', 'total_trend_last_3', 'total_acceleration',
    'improvement_streak', 'sn_to_cj_ratio', 'sn_improvement_last_3',
    'cj_improvement_last_3', 'comps_last_180_days',
    'avg_days_between_comps', 'comp_timing_deviation',
]

MODELS_DIR = Path(__file__).resolve().parent / "_models"
QUANTILES = (25, 50, 75, 99)

NAN = float("nan")
ATTEMPT_FIELDS = ("sn_1", "sn_2", "sn_3", "cj_1", "cj_2", "cj_3")

_boosters = None


def get_boosters():
    """Loads the four quantile models once per process (a warm serverless instance reuses them)."""
    global _boosters
    if _boosters is None:
        _boosters = {q: lgb.Booster(model_file=str(MODELS_DIR / f"lightgbm_q{q}.txt")) for q in QUANTILES}
    return _boosters


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _trend(prior: list[float]) -> float:
    """The pipeline's rolling(3, min_periods=2).apply(safe_polyfit) for the row after `prior`
    (the athlete's earlier values, oldest first).

    The pipeline's window is the last 3 values with NaN padding at the start of the history, so:
    1 prior value -> NaN; 2 -> 0 if they're equal, otherwise NaN (polyfit on a NaN gives NaN);
    3 or more -> 0 if the last three are equal, otherwise the slope of a straight-line fit."""
    window = prior[-3:]
    if len(window) < 2:
        return NAN
    if len(window) == 2:
        return 0.0 if window[0] == window[1] else NAN
    if window[0] == window[1] == window[2]:
        return 0.0
    return float(np.polyfit(range(3), window, 1)[0])


def _improvement_streak(totals: list[float]) -> float:
    """How many of the last three meet-to-meet steps were increases in total, matching the pipeline's
    (shift(1) > shift(2)).astype(int).rolling(3).sum(). A step that doesn't exist yet (history shorter
    than four meets) counts as not an increase. Needs at least two prior meets."""
    m = len(totals)
    if m < 2:
        return NAN

    def went_up(k: int) -> int:  # did meet k (1-based) beat meet k-1?
        return 1 if k >= 2 and totals[k - 1] > totals[k - 2] else 0

    return float(went_up(m) + went_up(m - 1) + went_up(m - 2))


def next_meet_features(history: list[dict], target_date, target_bodyweight: float) -> list[float]:
    """The model's 24 features, in FEATURE_COLS order, for a meet on target_date at target_bodyweight.

    `history` is the athlete's earlier meets as dicts shaped like rows of the meet_results table
    (date, bodyweight, sn_1..cj_3, best_sn, best_cj, total, bombed_out, gender). Missing values
    (None or NaN) are left as NaN here; predict_next_meet fills them with 0 exactly as training did.

    Two groups, as in the pipeline: performance-history features use only meets that were not
    bomb-outs (a bomb-out never reads as a collapse), while attendance features count every meet."""
    rows = sorted((r for r in history if not _missing(r.get("date"))), key=lambda r: _as_date(r["date"]))
    target = _as_date(target_date)
    dates = [_as_date(r["date"]) for r in rows]

    f = {c: NAN for c in FEATURE_COLS}
    f["Bodyweight"] = float(target_bodyweight)

    # ---- attendance: every meet, bomb-outs included
    k = len(rows)
    if k:
        f["Num Competitions"] = float(k)
        gaps = [NAN] + [float((dates[i] - dates[i - 1]).days) for i in range(1, k)]  # each meet's own gap
        recent = [g for g in gaps[-3:] if not math.isnan(g)]
        avg_gap = sum(recent) / len(recent) if recent else NAN
        days_since_last = float((target - dates[-1]).days)
        f["Days Since Last Comp"] = days_since_last
        f["avg_days_between_comps"] = avg_gap
        f["comp_timing_deviation"] = days_since_last - avg_gap
        f["comps_last_180_days"] = float(sum(1 for d in dates if (target - d).days <= 180))

    # ---- performance history: meets that weren't bomb-outs
    valid = [r for r in rows if not r.get("bombed_out")]
    m = len(valid)
    if m:
        vdates = [_as_date(r["date"]) for r in valid]
        totals = [float(r["total"]) for r in valid]
        snatch = [float(r["best_sn"]) for r in valid]
        cj = [float(r["best_cj"]) for r in valid]

        for field, col in zip(ATTEMPT_FIELDS, FEATURE_COLS[1:7]):
            f[col] = sum(1 for r in valid if _missing(r.get(field))) / m  # share of attempts missed

        f["best_snatch_to_date"] = max(snatch)
        f["best_cj_to_date"] = max(cj)
        best_total = max(totals)
        f["best_total_to_date"] = best_total
        f["Last Comp Total"] = totals[-1]
        last_best = max(i for i, t in enumerate(totals) if t == best_total)  # latest meet at the best total
        f["Days Since Best Total"] = float((target - vdates[last_best]).days)

        f["total_trend_last_3"] = _trend(totals)
        f["total_acceleration"] = f["total_trend_last_3"] - _trend(totals[:-1])
        f["improvement_streak"] = _improvement_streak(totals)
        f["sn_to_cj_ratio"] = snatch[-1] / cj[-1] if cj[-1] else NAN
        f["sn_improvement_last_3"] = _trend(snatch)
        f["cj_improvement_last_3"] = _trend(cj)

    gender = next((r.get("gender") for r in reversed(rows) if r.get("gender") in ("Men", "Women")), None)
    if gender:
        f["Gender Binary"] = 0.0 if gender == "Men" else 1.0

    return [f[c] for c in FEATURE_COLS]


def predict_next_meet(history: list[dict], target_date, target_bodyweight: float) -> dict[str, float]:
    """Predicted total (kg) at the 25th / 50th / 75th / 99th percentile for the meet described."""
    features = next_meet_features(history, target_date, target_bodyweight)
    x = np.nan_to_num(np.array([features], dtype=float), nan=0.0)  # training filled NaN with 0
    return {f"q{q}": float(booster.predict(x)[0]) for q, booster in get_boosters().items()}

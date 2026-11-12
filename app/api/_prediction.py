"""Predict an athlete's total at a future meet.

Rebuilds the 34 features the quantile models were trained on from the athlete's previous meets
plus the chosen meet date and bodyweight, in plain Python (no pandas: it would push the
deployed function over Vercel's size limit). Every feature mirrors transform/feature_engineering.py
exactly, quirks included; tests/check_prediction_features.py proves that against the real data.
If you change one side, change the other and re-run that check.

Since model v2 (2026-11-08) the models predict the CHANGE from the athlete's last real total (their
latest meet that wasn't a bomb-out); predict_next_meet adds it back (see models/train.py). Model v3
(2026-11-11) adds seven history features (add_v3_features in feature_engineering.py), mirrored below.

The leading underscore keeps Vercel from treating this file (or _models/) as an endpoint.
"""

import math
import re
from datetime import date, datetime
from pathlib import Path

import numpy as np

# Must equal QUANTILE_FEATURE_COLS in models/train.py: the models take features positionally, by index.
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
    'prev_division_code', 'career_days', 'meet_month',
    'sn_left_on_platform', 'cj_left_on_platform', 'total_rate_per_month', 'change_volatility',
    'gap_from_best', 'career_rate_per_month', 'bodyweight_trend_per_month',
]

MODELS_DIR = Path(__file__).resolve().parent / "_models"
QUANTILES = (1, 25, 50, 75, 99)

NAN = float("nan")
ATTEMPT_FIELDS = ("sn_1", "sn_2", "sn_3", "cj_1", "cj_2", "cj_3")
# Model v3: same as feature_engineering.py's DAYS_PER_MONTH and SLOPE_WINDOW.
DAYS_PER_MONTH = 30.44
SLOPE_WINDOW = 5
EPOCH = date(1970, 1, 1)

_boosters = None

# LightGBM's kZeroThreshold: the float 1e-35, widened to a double.
ZERO_THRESHOLD = 1.0000000180025095e-35


class TreeModel:
    """A LightGBM model read straight from its native text file (what models/train.py writes), so the
    deployed API doesn't need the lightgbm package. That package's Linux build needs the system library
    libgomp.so.1 (OpenMP), which Vercel's Python runtime doesn't provide - every prediction failed in
    production until this replaced it.

    Only what these models use is supported: one output, numerical splits with no special missing-value
    handling (inputs are NaN-filled with 0 before predicting, as in training), no categorical splits, no
    linear trees. Anything else is refused at load time rather than predicted wrongly - e.g. a future
    retrain with a categorical feature would need support added here first.
    tests/check_tree_model.py checks the predictions match the lightgbm package exactly.
    """

    def __init__(self, text: str):
        header, _, body = text.partition("\nTree=")
        settings = dict(line.split("=", 1) for line in header.splitlines() if "=" in line)
        if settings.get("num_tree_per_iteration", "1") != "1" or settings.get("num_class", "1") != "1":
            raise ValueError("only single-output models are supported")
        if "average_output" in header.splitlines():
            raise ValueError("random-forest mode (average_output) is not supported")
        # Objectives whose prediction is the raw summed score; others (binary, poisson, ...) transform it.
        if settings.get("objective", "").split(" ")[0] not in {"quantile", "regression", "regression_l1", "huber", "fair"}:
            raise ValueError(f"objective {settings.get('objective')!r} is not supported")

        self.trees = []
        for block in body.split("\nTree="):
            block = block.split("end of trees")[0]
            fields = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
            if "num_leaves" not in fields:
                continue
            if fields.get("num_cat", "0") != "0" or fields.get("is_linear", "0") != "0":
                raise ValueError("categorical splits and linear trees are not supported")
            leaf_value = [float(v) for v in fields["leaf_value"].split()]
            if int(fields["num_leaves"]) == 1:
                self.trees.append(([], [], [], [], leaf_value))
                continue
            if any(int(d) not in (0, 2) for d in fields["decision_type"].split()):
                # bit 0 = categorical, bits 2-3 = missing-value type; only bit 1 (default left) is
                # allowed, and with no missing-value type it never comes into play.
                raise ValueError("only plain numerical splits are supported")
            self.trees.append((
                [int(v) for v in fields["split_feature"].split()],
                [float(v) for v in fields["threshold"].split()],
                [int(v) for v in fields["left_child"].split()],
                [int(v) for v in fields["right_child"].split()],
                leaf_value,
            ))
        if not self.trees:
            raise ValueError("no trees found in the model file")

    def predict_one(self, x: list[float]) -> float:
        """Raw score for one row: the sum of one leaf per tree, added in tree order as LightGBM does.
        (The quantile objective has no output transform, and leaf values already include the learning
        rate and, in the first tree, the starting average.)"""
        # LightGBM treats any input within +-kZeroThreshold of zero as exactly 0 before walking the
        # trees, and some splits sit right at +-kZeroThreshold, so do the same.
        x = [0.0 if abs(v) <= ZERO_THRESHOLD else v for v in x]
        total = 0.0
        for split_feature, threshold, left_child, right_child, leaf_value in self.trees:
            node = 0
            if split_feature:
                while node >= 0:
                    if x[split_feature[node]] <= threshold[node]:
                        node = left_child[node]
                    else:
                        node = right_child[node]
                node = ~node  # children < 0 are leaves, stored as ~leaf_index
            total += leaf_value[node]
        return total


def _load_booster(path: Path) -> TreeModel:
    # Read as text: Python normalizes line endings on read, so a copy that picked up Windows CRLF
    # endings (git's autocrlf does this on checkout) still parses.
    return TreeModel(path.read_text(encoding="utf-8"))


def get_boosters():
    """Loads the four quantile models once per process (a warm serverless instance reuses them)."""
    global _boosters
    if _boosters is None:
        _boosters = {q: _load_booster(MODELS_DIR / f"lightgbm_q{q}.txt") for q in QUANTILES}
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


def _slope_per_month(y: list, days: list) -> float:
    """feature_engineering.prior_slope_per_month for the row after these meets: the least-squares slope
    of y per month over the last SLOPE_WINDOW of them, skipping missing values; NaN with fewer than 2 or
    all on one day. Same numpy arithmetic, in the same order, so the result matches to the last digit."""
    yy = np.array([NAN if _missing(v) else float(v) for v in y[-SLOPE_WINDOW:]], dtype=float)
    tt = np.array(days[-SLOPE_WINDOW:], dtype=float)
    ok = ~np.isnan(yy) & ~np.isnan(tt)
    if ok.sum() < 2:
        return NAN
    tc = tt[ok] - tt[ok].mean()
    den = (tc * tc).sum()
    if not den > 0:
        return NAN
    return float((tc * (yy[ok] - yy[ok].mean())).sum() / den * DAYS_PER_MONTH)


def _left_on_platform(meet: dict, lift: str, best_field: str) -> float:
    """Heaviest weight attempted (made or missed) minus heaviest made, at one meet, for one lift."""
    tried = [float(meet[f"{lift}_{n}_attempted"]) for n in (1, 2, 3) if not _missing(meet.get(f"{lift}_{n}_attempted"))]
    best = meet.get(best_field)
    if not tried or _missing(best):
        return NAN
    return max(tried) - float(best)


def _division_code(weight_category) -> float:
    """The age division in a weight category as an ordered number - must match division_code in
    transform/feature_engineering.py: 0 = 11 & Under, 1 = 13 & Under, 2 = 14-15, 3 = 16-17, 4 = Junior,
    5 = Open, 6+ = Masters by bracket (35-39 = 6, 40-44 = 7, ...); NaN if it can't be read."""
    s = re.sub(r"^(Men's|Women's)\s*|\s*(Men's|Women's)\s*", " ", str(weight_category))
    s = re.sub(r"\s*\d+\+?\s*kg\+?$", "", s).strip()
    if "Under" in s:
        return 1.0 if s.startswith("13") else 0.0
    if s.startswith("14-15"):
        return 2.0
    if s.startswith("16-17"):
        return 3.0
    if s.startswith("Junior"):
        return 4.0
    if s.startswith("Open"):
        return 5.0
    m = re.match(r"Masters \((\d+)", s)
    if m:
        return float(6 + (int(m.group(1)) - 35) // 5)
    return NAN


def next_meet_features(history: list[dict], target_date, target_bodyweight: float) -> list[float]:
    """The model's 34 features, in FEATURE_COLS order, for a meet on target_date at target_bodyweight.

    `history` is the athlete's earlier meets as dicts shaped like rows of the meet_results table
    (date, bodyweight, sn_1..cj_3, sn_1_attempted..cj_3_attempted, best_sn, best_cj, total, bombed_out, gender,
    weight_category). Missing values
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
        # model v2: the division at their latest meet, career length, and the month
        f["prev_division_code"] = _division_code(rows[-1].get("weight_category"))
        f["career_days"] = float((target - dates[0]).days)
        # model v3: bodyweight trend in kg per month over the last few meets (every meet)
        f["bodyweight_trend_per_month"] = _slope_per_month(
            [r.get("bodyweight") for r in rows], [float((d - EPOCH).days) for d in dates])
    f["meet_month"] = float(target.month)

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

        # model v3
        f["sn_left_on_platform"] = _left_on_platform(valid[-1], "sn", "best_sn")
        f["cj_left_on_platform"] = _left_on_platform(valid[-1], "cj", "best_cj")
        vdays = [float((d - EPOCH).days) for d in vdates]
        f["total_rate_per_month"] = _slope_per_month(totals, vdays)
        if m >= 3:  # spread of the last few meet-to-meet changes
            f["change_volatility"] = float(np.diff(np.array(totals[-(SLOPE_WINDOW + 1):], dtype=float)).std())
        f["gap_from_best"] = best_total - totals[-1]
        span = vdays[-1] - vdays[0]
        if span > 0:
            f["career_rate_per_month"] = (totals[-1] - totals[0]) / span * DAYS_PER_MONTH

    gender = next((r.get("gender") for r in reversed(rows) if r.get("gender") in ("Men", "Women")), None)
    if gender:
        f["Gender Binary"] = 0.0 if gender == "Men" else 1.0

    return [f[c] for c in FEATURE_COLS]


def predict_next_meet(history: list[dict], target_date, target_bodyweight: float) -> dict[str, float]:
    """Predicted total (kg) at each percentile in QUANTILES for the meet described, keyed "q1" ... "q99":
    the athlete's last real total plus the models' predicted change. Raises ValueError if the athlete has
    no real total to start from (every meet a bomb-out), which the endpoint checks for first."""
    features = next_meet_features(history, target_date, target_bodyweight)
    last_total = features[FEATURE_COLS.index("Last Comp Total")]
    if math.isnan(last_total) or last_total <= 0:
        raise ValueError("no completed total to predict from")
    x = [0.0 if v is None or math.isnan(v) else float(v) for v in features]  # training filled NaN with 0
    return {f"q{q}": last_total + model.predict_one(x) for q, model in get_boosters().items()}

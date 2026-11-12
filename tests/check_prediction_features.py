"""Proves app/api/_prediction.py builds the model's features exactly the way the pipeline did.

For every real meet in data/meet_results_FEATURES.csv (after the athlete's first), pretend that meet
hasn't happened yet: hand the calculator only the athlete's EARLIER meets, plus that meet's date and
bodyweight, and compare the 34 features it returns with the values the pipeline stored for that row.
They should be identical. Bomb-out meets only have attendance features in the file, so only those
are compared for them.

The history rows are shaped like the Supabase meet_results table (missed attempts as null, no
miss-flag columns), so this also checks that deriving "missed" from a null attempt matches the
pipeline's flags.

Needs the local-only FEATURES.csv. Run from the repo root:  python tests/check_prediction_features.py
"""

import math
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api"))
sys.path.insert(0, str(ROOT / "models"))

import _prediction as P  # noqa: E402
import train as T  # noqa: E402  (only for FEATURE_COLS)

FEATURES_CSV = ROOT / "data" / "meet_results_FEATURES.csv"
ATTENDANCE = {"Bodyweight", "Num Competitions", "Days Since Last Comp", "comps_last_180_days",
              "avg_days_between_comps", "comp_timing_deviation",
              "prev_division_code", "career_days", "meet_month",  # model v2: also over every meet
              "bodyweight_trend_per_month"}  # model v3
ATTEMPT_COLS = ["Sn#1", "Sn#2", "Sn#3", "CJ#1", "CJ#2", "CJ#3"]
TRIED_COLS = [f"{c}_attempted" for c in ATTEMPT_COLS]  # model v3: weight attempted, made or missed
ATTEMPT_KEYS = ["sn_1", "sn_2", "sn_3", "cj_1", "cj_2", "cj_3"]


def none_if_nan(v):
    return None if isinstance(v, float) and math.isnan(v) else v


def same(a, b):
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b


def close(a, b):
    """Equal up to floating-point noise (pandas' rolling means and slopes differ from a plain sum
    or fit in the last digit or two, which no tree split can ever see)."""
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def main():
    assert P.FEATURE_COLS == T.QUANTILE_FEATURE_COLS, "FEATURE_COLS in app/api/_prediction.py differs from QUANTILE_FEATURE_COLS in models/train.py"
    print("FEATURE_COLS match models/train.py")

    cols = ["Name", "Date", "Bodyweight", "Gender", "Best Sn", "Best CJ", "Total", "bombed_out", "Weight Category"] + ATTEMPT_COLS + TRIED_COLS
    cols += [c for c in T.QUANTILE_FEATURE_COLS if c not in cols]
    df = pd.read_csv(FEATURES_CSV, usecols=cols)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 1  # check every Nth athlete
    mismatches = Counter()      # feature -> rows that differ by more than floating-point noise
    noise = Counter()           # feature -> rows that differ only in the last digits
    compared = Counter()        # feature -> rows compared
    examples = {}               # feature -> first few (athlete, meet index, expected, got)
    exp_batch, got_batch = [], []   # full feature rows, to compare the models' actual predictions
    gender_convention = [0]     # meets where the target's own gender differs from the athlete's last known one
    skipped_undated = 0
    rows_checked = 0
    t0 = time.time()

    for n_athlete, (name, g) in enumerate(df.groupby("Name", sort=False)):
        if len(g) < 2 or n_athlete % every:
            continue
        if g["Date"].isna().any():       # the API ignores undated meets, the pipeline sorts them last
            skipped_undated += 1
            continue

        rows = [
            {
                "date": rec["Date"].date(),
                "bodyweight": none_if_nan(rec["Bodyweight"]),
                "best_sn": none_if_nan(rec["Best Sn"]),
                "best_cj": none_if_nan(rec["Best CJ"]),
                "total": none_if_nan(rec["Total"]),
                "bombed_out": bool(rec["bombed_out"]),
                "gender": rec["Gender"] if isinstance(rec["Gender"], str) else None,
                "weight_category": rec["Weight Category"] if isinstance(rec["Weight Category"], str) else None,
                **{k: none_if_nan(rec[c]) for k, c in zip(ATTEMPT_KEYS, ATTEMPT_COLS)},
                **{f"{k}_attempted": none_if_nan(rec[c]) for k, c in zip(ATTEMPT_KEYS, TRIED_COLS)},
            }
            for rec in g[["Date", "Bodyweight", "Best Sn", "Best CJ", "Total", "bombed_out", "Gender", "Weight Category"] + ATTEMPT_COLS + TRIED_COLS].to_dict("records")
        ]
        expected = g[T.QUANTILE_FEATURE_COLS].to_numpy(dtype=float)
        bombed = g["bombed_out"].to_numpy(dtype=bool)

        for i in range(1, len(rows)):
            got = P.next_meet_features(rows[:i], rows[i]["date"], rows[i]["bodyweight"])
            rows_checked += 1
            for j, col in enumerate(T.QUANTILE_FEATURE_COLS):
                if bombed[i] and col not in ATTENDANCE:
                    continue
                if col == "Gender Binary":
                    # A future meet has no weight category of its own, so the calculator uses the athlete's
                    # most recent known gender, while the pipeline used each meet's own. Count where they
                    # differ (rare data quirks) but don't call it a calculator error.
                    compared[col] += 1
                    if not same(float(expected[i, j]), got[j]):
                        gender_convention[0] += 1
                    continue
                compared[col] += 1
                e = float(expected[i, j])
                if not same(e, got[j]):
                    if close(e, got[j]):
                        noise[col] += 1
                    else:
                        mismatches[col] += 1
                        examples.setdefault(col, [])
                        if len(examples[col]) < 4:
                            examples[col].append((name, i, e, got[j]))
            if not bombed[i]:
                exp_batch.append(expected[i])
                got_batch.append(got)

    print(f"\nchecked {rows_checked:,} meets in {time.time() - t0:.0f}s "
          f"({skipped_undated} athletes skipped for having an undated meet)")
    print(f"{'feature':28} {'compared':>9} {'last-digit noise':>17} {'REAL mismatch':>14}")
    total_bad = 0
    for col in T.QUANTILE_FEATURE_COLS:
        bad = mismatches[col]
        total_bad += bad
        print(f"{col:28} {compared[col]:9,} {noise[col]:17,} {bad:14,}" + ("   <-- DIFFERS" if bad else ""))
    for col, ex in examples.items():
        print(f"\nexamples for {col} (athlete, prior meets, pipeline value, calculator value):")
        for e in ex:
            print("   ", e)

    print(f"\nGender Binary: the target meet's own gender differed from the athlete's last known gender on "
          f"{gender_convention[0]:,} of {compared['Gender Binary']:,} meets ({gender_convention[0] / compared['Gender Binary']:.2%}) - "
          "a convention difference (see above), not compared as an error")

    # The test that matters most: do the models predict the same thing from both feature sets?
    # Gender is set equal first so this isolates the calculator's arithmetic from that convention.
    import numpy as np
    x_exp = np.nan_to_num(np.array(exp_batch, dtype=float), nan=0.0)
    x_got = np.nan_to_num(np.array(got_batch, dtype=float), nan=0.0)
    gi = T.QUANTILE_FEATURE_COLS.index("Gender Binary")
    x_got[:, gi] = x_exp[:, gi]
    print(f"\nmodel predictions on {len(x_exp):,} meets, pipeline features vs calculator features:")
    print("  (the few last-digit rounding differences above can tip a tree split the other way; the effect is tiny)")
    worst_p999 = 0.0
    # The lightgbm package here (fast on 250K rows; local only): tests/check_tree_model.py proves the
    # API's own pure-Python reader of these model files predicts identically.
    import lightgbm as lgb
    for q in P.QUANTILES:
        booster = lgb.Booster(model_str=(P.MODELS_DIR / f"lightgbm_q{q}.txt").read_text(encoding="utf-8"))
        diff = np.abs(booster.predict(x_exp) - booster.predict(x_got))
        p999 = float(np.percentile(diff, 99.9))
        worst_p999 = max(worst_p999, p999)
        print(f"  q{q}: differs by >0.001 kg on {(diff > 1e-3).mean():.2%} of meets | 99.9th percentile {p999:.3f} kg | max {diff.max():.2f} kg")

    # Pass criteria: no real feature differences, and predictions agree to within 1 kg for 99.9% of meets.
    ok = total_bad == 0 and worst_p999 < 1.0
    print("\nRESULT:", "PASS - features match the pipeline and predictions agree" if ok
          else f"FAIL - {total_bad:,} real feature differences; worst 99.9th-percentile prediction difference {worst_p999:.3f} kg")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

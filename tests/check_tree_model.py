"""Proves the API's own model reader (TreeModel in app/api/_prediction.py) predicts exactly what the
lightgbm package does with the same model files.

The deployed API can't use the lightgbm package (its Linux build needs libgomp.so.1, which Vercel's
Python runtime lacks), so it walks the trees itself. This compares the two on:
  - every 2024+ non-bomb-out row of the local FEATURES.csv (the models' test set), NaN filled with 0
    exactly as the API does, and
  - rows whose values sit exactly on split thresholds, where a "<" vs "<=" mistake would show,
and checks that model files using features the reader doesn't support are refused at load time.

Needs the lightgbm package (local only) and the local FEATURES.csv. Run from the repo root:
    python tests/check_tree_model.py [--every N]     (--every 10 checks every 10th test row; faster)
"""

import argparse
import random
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api"))

import _prediction as P  # noqa: E402

FEATURES_CSV = ROOT / "data" / "meet_results_FEATURES.csv"

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def compare(label, rows, ours, theirs):
    preds_ours = np.array([ours.predict_one(list(r)) for r in rows])
    preds_theirs = theirs.predict(rows)
    diff = np.abs(preds_ours - preds_theirs)
    check(label, diff.max() == 0.0,
          f"{len(rows):,} rows, max difference {diff.max():.3g}, {int((diff > 0).sum())} rows differ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--every", type=int, default=1, help="check every Nth test row")
    args = parser.parse_args()

    df = pd.read_csv(FEATURES_CSV, usecols=["Date", "bombed_out", *P.FEATURE_COLS], low_memory=False)
    df = df[(pd.to_datetime(df["Date"], errors="coerce") >= "2024-01-01") & ~df["bombed_out"].astype(bool)]
    test_rows = df[P.FEATURE_COLS].fillna(0).to_numpy(dtype=float)[:: args.every]

    rng = random.Random(0)
    for q in P.QUANTILES:
        text = (P.MODELS_DIR / f"lightgbm_q{q}.txt").read_text(encoding="utf-8")
        ours, theirs = P.TreeModel(text), lgb.Booster(model_str=text)

        compare(f"q{q}: test-set predictions identical", test_rows, ours, theirs)

        # Rows built from the models' own thresholds: each feature set to a threshold used on it
        # (or just either side of one), so many comparisons land exactly on a split.
        thresholds = {}
        for split_feature, threshold, *_ in ours.trees:
            for f, t in zip(split_feature, threshold):
                thresholds.setdefault(f, []).append(t)
        edge_rows = []
        for _ in range(2000):
            row = test_rows[rng.randrange(len(test_rows))].copy()
            for f, ts in thresholds.items():
                if rng.random() < 0.5:
                    t = rng.choice(ts)
                    row[f] = rng.choice([t, np.nextafter(t, -np.inf), np.nextafter(t, np.inf)])
            edge_rows.append(row)
        compare(f"q{q}: values on split thresholds give identical predictions", np.array(edge_rows), ours, theirs)

    # Unsupported model features must be refused, not silently mispredicted.
    text = (P.MODELS_DIR / "lightgbm_q50.txt").read_text(encoding="utf-8")
    first_tree_end = text.index("\n\n", text.index("Tree=0"))
    first_tree = text[:first_tree_end]
    variants = {
        "a categorical split": first_tree.replace("decision_type=2 ", "decision_type=3 ", 1),
        "a missing-value split type": first_tree.replace("decision_type=2 ", "decision_type=10 ", 1),
        "a categorical feature": first_tree.replace("num_cat=0", "num_cat=1", 1),
        "a linear tree": first_tree.replace("is_linear=0", "is_linear=1", 1),
        "an objective that transforms the score": first_tree.replace("objective=quantile", "objective=poisson", 1),
    }
    for name, changed_tree in variants.items():
        assert changed_tree != first_tree, name
        try:
            P.TreeModel(changed_tree + text[first_tree_end:])
            refused = False
        except ValueError:
            refused = True
        check(f"a model with {name} is refused", refused)

    print()
    print(f"{len(failures)} FAILED: {failures}" if failures else "all checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

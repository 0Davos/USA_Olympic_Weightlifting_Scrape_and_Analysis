# Segment-aware model evaluation: percentile-based MAE breakdown + residual distribution
#
# Note: the notebook version of this evaluation compared performance_percentile
# (a 0-100 scale column) against 0.5/0.85 thresholds - effectively a bug that left
# "top 15%" covering nearly the entire test set. Fixed here to use 50/85, matching
# the actual scale. See docs/findings.md for how this affected the originally-published
# segment MAE figures.

import os
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_absolute_error

from train import FEATURE_COLS, FEATURES_CSV_PATH, prepare_train_test, train_baseline_models, tune_xgboost

SEGMENT_BINS = [0, 50, 85, 100]
SEGMENT_LABELS = ["Bottom 50%", "50–85%", "Top 15%"]


def eval_segment(segment, model):
    X = segment[FEATURE_COLS].fillna(0)
    y_true = segment['Total']
    y_pred = model.predict(X)
    return mean_absolute_error(y_true, y_pred)


def segment_aware_comparison(test, models):
    bottom_50 = test[test['performance_percentile'] < 50]
    mid_50_85 = test[(test['performance_percentile'] >= 50) & (test['performance_percentile'] < 85)]
    top_15 = test[test['performance_percentile'] >= 85]

    print("Model Performance Comparison (Segment Aware):")
    for name, model in models.items():
        mae_bottom = eval_segment(bottom_50, model)
        mae_mid = eval_segment(mid_50_85, model)
        mae_top = eval_segment(top_15, model)
        print("-" * 64)
        print(f"Model: {name}")
        print(f"0th-50th   Percentile MAE: {mae_bottom:.2f}kg")
        print(f"50th-85th  Percentile MAE: {mae_mid:.2f}kg")
        print(f"85th-100th Percentile MAE: {mae_top:.2f}kg")


def plot_residuals_by_segment(test, model, show=True):
    eval_df = test.copy()
    eval_df["Residual"] = eval_df["Total"] - model.predict(eval_df[FEATURE_COLS])

    eval_df["Segment"] = pd.cut(
        eval_df["performance_percentile"],
        bins=SEGMENT_BINS,
        labels=SEGMENT_LABELS,
    )

    plt.figure(figsize=(8, 6))
    eval_df.boxplot(column="Residual", by="Segment", grid=False)
    plt.axhline(0, color="red", linestyle="--")
    plt.title("Residual Distribution by Performance Percentile Segment")
    plt.suptitle("")
    plt.xlabel("Performance Segment (Bodyweight-Adjusted)")
    plt.ylabel("Residual (kg)")
    if show:
        plt.show()
    return eval_df


if __name__ == '__main__':
    df = pd.read_csv(FEATURES_CSV_PATH)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    train, test, X_train, X_test, y_train, y_test = prepare_train_test(df)
    models = train_baseline_models(X_train, y_train)
    xgb_tuned = tune_xgboost(X_train, y_train)

    eval_models = {
        'Linear Regression': models['Linear Regression'],
        'Random Forest': models['Random Forest'],
        'XGBoost': xgb_tuned,
    }

    segment_aware_comparison(test, eval_models)
    plot_residuals_by_segment(test, xgb_tuned)

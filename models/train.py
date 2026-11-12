# Model training: meet_results_FEATURES.csv -> trained models + comparison metrics
#
# Trains on pre-2024 competitions, evaluates on 2024+ (temporal split, not random,
# to simulate predicting future performance from past history).

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_pinball_loss, make_scorer
from sklearn.model_selection import RandomizedSearchCV
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_FEATURES.csv")
SAVED_MODELS_DIR = os.path.join(SCRIPT_DIR, "saved")
SERVING_MODELS_DIR = os.path.join(SCRIPT_DIR, "..", "app", "api", "_models")

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

XGB_PARAM_GRID = {
    'max_depth': [5, 6, 7, 8, 9],
    'learning_rate': [0.02, 0.03, 0.04, 0.05, 0.07],
    'n_estimators': [300, 350, 400, 450, 500],
    'subsample': [1.0],
}

LGBM_PARAM_GRID = {
    'num_leaves': [20, 31, 40, 50, 60],
    'max_depth': [5, 6, 7, 8, 9],
    'learning_rate': [0.02, 0.03, 0.04, 0.05, 0.07],
    'n_estimators': [300, 350, 400, 450, 500],
    'min_child_samples': [10, 20, 30],
}

CATBOOST_PARAM_GRID = {
    'depth': [5, 6, 7, 8, 9],
    'learning_rate': [0.02, 0.03, 0.04, 0.05, 0.07],
    'iterations': [300, 350, 400, 450, 500],
    'l2_leaf_reg': [1, 3, 5, 7, 9],
}

# The website draws bands between neighbouring quantiles, mirrored around the median (1st-25th-50th
# below it, 50th-75th-99th above). The 1st was added 2026-11-08 to the original four.
QUANTILES = [0.01, 0.25, 0.50, 0.75, 0.99]

# ---- prediction models (the website's bands), "model v2" since 2026-11-08
# They predict the CHANGE in total from the athlete's last real (non-bomb-out) total, which the API adds
# back. Predicting the total itself capped elite lifters near the highest totals seen in training (the
# top of the bands was too low for them); a change has no such ceiling. They also get three more features
# known before a meet. Backtest on the 2024+ test meets (48,876, returning athletes), current settings:
# median error 6.87 -> 6.58kg (vs 8.16kg for "same as last total"); elite (best 330kg+) 99th-percentile
# coverage 93.4% -> 96.8%. Must equal FEATURE_COLS in app/api/_prediction.py (the API passes features by
# position; tests/check_prediction_features.py checks they match).
#
# Model v3 (2026-11-11) adds seven more history features (transform/feature_engineering.py, add_v3_features):
# weight left on the platform at the last meet (per lift), trend and career improvement in kg per month,
# the spread of recent changes, and the gap from the best; plus the bodyweight trend. Backtest on the 2024+
# test meets, scored at the last recorded bodyweight as the website predicts: median error 6.641 -> 6.558kg,
# average pinball loss 1.900 -> 1.871, 1st-99th band 46.9 -> 45.0kg at the same coverage. The shipped models
# are then trained on every meet (train_lightgbm_quantiles(final=True)), not just pre-2024 ones.
V2_EXTRA_COLS = ['prev_division_code', 'career_days', 'meet_month']
V3_EXTRA_COLS = ['sn_left_on_platform', 'cj_left_on_platform', 'total_rate_per_month', 'change_volatility',
                 'gap_from_best', 'career_rate_per_month', 'bodyweight_trend_per_month']
QUANTILE_FEATURE_COLS = FEATURE_COLS + V2_EXTRA_COLS + V3_EXTRA_COLS

# The settings each percentile's model is trained with: what RandomizedSearchCV picked for the original
# total-predicting models (2026-09-30; the 1st percentile 2026-11-08), kept for v2. A v2 tuning search was
# tried 2026-11-08 and not adopted (same accuracy; it widened the elite bands and pulled some elite lifters'
# 99th percentile below their last total - see ROADMAP.md, model v2).
QUANTILE_PARAMS = {
    0.01: dict(learning_rate=0.05, num_leaves=20, max_depth=5, min_child_samples=10, n_estimators=350),
    0.25: dict(learning_rate=0.07, num_leaves=60, max_depth=7, min_child_samples=30, n_estimators=500),
    0.50: dict(learning_rate=0.04, num_leaves=60, max_depth=8, min_child_samples=30, n_estimators=450),
    0.75: dict(learning_rate=0.04, num_leaves=60, max_depth=8, min_child_samples=30, n_estimators=450),
    0.99: dict(learning_rate=0.07, num_leaves=50, max_depth=6, min_child_samples=30, n_estimators=400),
}


def prepare_train_test(df):
    # Bomb-outs (Total=0) are a different kind of event, not a weak performance -
    # kept in the data for the website, but never a training/eval target here.
    df = df[~df['bombed_out']]

    # Split by date
    train = df[df['Date'] < '2024-01-01']
    test = df[df['Date'] >= '2024-01-01']

    X_train = train[FEATURE_COLS].fillna(0)
    y_train = train['Total']
    X_test = test[FEATURE_COLS].fillna(0)
    y_test = test['Total']

    return train, test, X_train, X_test, y_train, y_test


def train_baseline_models(X_train, y_train):
    lr = LinearRegression()
    lr.fit(X_train, y_train)

    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)

    xgb = XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    xgb.fit(X_train, y_train)

    catboost_model = CatBoostRegressor(iterations=100, depth=6, learning_rate=0.1, random_state=42, verbose=False)
    catboost_model.fit(X_train, y_train)

    lgbm_model = LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1)
    lgbm_model.fit(X_train, y_train)

    return {'Linear Regression': lr, 'Random Forest': rf, 'XGBoost': xgb, 'CatBoost':catboost_model, 'LightGBM':lgbm_model}


def tune_xgboost(X_train, y_train):
    xgb_tuned = RandomizedSearchCV(
        XGBRegressor(random_state=42, n_jobs=-1),
        XGB_PARAM_GRID,
        n_iter=10,
        cv=5,
        scoring='neg_mean_absolute_error',
        random_state=42,
        verbose=2,
    )
    xgb_tuned.fit(X_train, y_train)

    print(f"\nXGBoost Best params: {xgb_tuned.best_params_}")
    print(f"XGBoost Best MAE: {-xgb_tuned.best_score_:.2f}kg")

    return xgb_tuned


def tune_lightgbm(X_train, y_train):
    lgbm_tuned = RandomizedSearchCV(
        LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1),
        LGBM_PARAM_GRID,
        n_iter=10,
        cv=5,
        scoring='neg_mean_absolute_error',
        random_state=42,
        verbose=2,
    )
    lgbm_tuned.fit(X_train, y_train)

    print(f"\nLightGBM Best params: {lgbm_tuned.best_params_}")
    print(f"LightGBM Best MAE: {-lgbm_tuned.best_score_:.2f}kg")

    return lgbm_tuned


def tune_catboost(X_train, y_train):
    catboost_tuned = RandomizedSearchCV(
        CatBoostRegressor(random_state=42, verbose=False, thread_count=-1),
        CATBOOST_PARAM_GRID,
        n_iter=10,
        cv=5,
        scoring='neg_mean_absolute_error',
        random_state=42,
        verbose=2,
    )
    catboost_tuned.fit(X_train, y_train)

    print(f"\nCatBoost Best params: {catboost_tuned.best_params_}")
    print(f"CatBoost Best MAE: {-catboost_tuned.best_score_:.2f}kg")

    return catboost_tuned


def save_quantile_models(quantile_models, output_dir=SAVED_MODELS_DIR):
    """Saves each quantile model to disk via joblib, so they can be reloaded for
    predictions later without re-running the tuning search. Saves .best_estimator_
    rather than the full RandomizedSearchCV object, since the search object also
    carries CV history/metadata that isn't needed for future predictions."""
    os.makedirs(output_dir, exist_ok=True)

    for q, model in quantile_models.items():
        estimator = model.best_estimator_ if hasattr(model, 'best_estimator_') else model
        filename = f"lightgbm_q{round(q * 100)}.pkl"
        filepath = os.path.join(output_dir, filename)
        joblib.dump(estimator, filepath)
        print(f"Saved quantile {q:.2f} model to {filepath}")
        save_serving_model(estimator, q)


def save_serving_model(estimator, q, output_dir=SERVING_MODELS_DIR):
    """Writes the model in LightGBM's native text format for the website's API. Unlike the
    joblib pickle, a native booster loads with lightgbm.Booster alone - no scikit-learn - which
    keeps the deployed function under Vercel's size limit. Lives under app/ because that is the
    only part of the repo the website deploys."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"lightgbm_q{round(q * 100)}.txt")
    estimator.booster_.save_model(filepath)
    print(f"Saved quantile {q:.2f} serving model to {filepath}")


def prepare_quantile_train_test(df):
    """Train/test split for the prediction models: same date split as prepare_train_test, but only meets
    with a last real total to predict a change from (an athlete's first meet has none), and the target is
    Total - Last Comp Total. Returns train, test, X_train, X_test, y_train (change), y_test (change)."""
    df = df[~df['bombed_out'] & (df['Last Comp Total'] > 0)]
    train = df[df['Date'] < '2024-01-01']
    test = df[df['Date'] >= '2024-01-01']
    X_train = train[QUANTILE_FEATURE_COLS].fillna(0)
    X_test = test[QUANTILE_FEATURE_COLS].fillna(0)
    y_train = train['Total'] - train['Last Comp Total']
    y_test = test['Total'] - test['Last Comp Total']
    return train, test, X_train, X_test, y_train, y_test


def report_quantile_calibration(quantile_models, test, X_test):
    """Coverage of each percentile on the test meets (the share of actual totals at or below the predicted
    one, which should equal the percentile), overall and by athlete level, plus the median's error. The
    outputs are sorted per row first, as the API does, since independent models can cross."""
    qs = sorted(quantile_models)
    last = test['Last Comp Total'].to_numpy()
    actual = test['Total'].to_numpy()
    preds = np.sort(np.vstack([last + quantile_models[q].predict(X_test) for q in qs]), axis=0)
    naive = np.abs(actual - last).mean()
    print(f"\nPrediction models - calibration on {len(test):,} test meets (naive 'same as last total' error {naive:.2f}kg)")
    print("-" * 72)
    for i, q in enumerate(qs):
        print(f"Quantile {q:.2f} | Target coverage: {q:6.1%} | Actual coverage: {(actual <= preds[i]).mean():6.1%}")
    if 0.50 in qs:
        print(f"Median error: {np.abs(actual - preds[qs.index(0.50)]).mean():.2f}kg")
    levels = pd.cut(test['best_total_to_date'], [0, 200, 250, 300, 330, 10000], right=False,
                    labels=['<200', '200-250', '250-300', '300-330', '330+']).to_numpy()
    for lv in ['<200', '200-250', '250-300', '300-330', '330+']:
        sel = levels == lv
        cov = ' / '.join(f"{(actual[sel] <= preds[i][sel]).mean():.1%}" for i in range(len(qs)))
        print(f"  best total {lv:>7} (n={sel.sum():,}): coverage {cov}")


def _fit_quantiles(X, y, quantiles, params):
    models = {}
    for q in quantiles:
        print(f"Training LightGBM quantile model for q={q} with {params[q]}...")
        models[q] = LGBMRegressor(
            objective='quantile', alpha=q, random_state=42, n_jobs=-1, verbose=-1, **params[q]
        ).fit(X, y)
    return models


def train_lightgbm_quantiles(df, quantiles=QUANTILES, params=QUANTILE_PARAMS, final=True):
    """Trains one LightGBM model per quantile with the given settings (no search) on the pre-2024 meets and
    prints the calibration check on the 2024+ ones. With final=True (the default since model v3) it then
    trains them again on every meet, so the website's models learn from the newest results too, and saves
    those; with final=False it saves the pre-2024 models that were checked. Seconds per model, unlike tuning."""
    train, test, X_train, X_test, y_train, y_test = prepare_quantile_train_test(df)
    quantile_models = _fit_quantiles(X_train, y_train, quantiles, params)
    report_quantile_calibration(quantile_models, test, X_test)
    if final:
        print(f"\nTraining the final models on all {len(X_train) + len(X_test):,} meets...")
        quantile_models = _fit_quantiles(pd.concat([X_train, X_test]), pd.concat([y_train, y_test]),
                                         quantiles, params)
    save_quantile_models(quantile_models)
    return quantile_models


def tune_lightgbm_quantiles(df, quantiles=QUANTILES):
    """Tunes one LightGBM model per quantile in `quantiles` (default: all of QUANTILES) via
    RandomizedSearchCV. Scored on pinball loss at that quantile's specific alpha,
    not MAE - MAE would push hyperparameters toward minimizing average error, which
    fights against what a quantile model (other than roughly the median) is actually
    trying to do. `alpha` stays fixed per model; only the other hyperparameters in
    LGBM_PARAM_GRID are searched. Prints an empirical coverage check for each tuned
    quantile: the fraction of actual test-set totals falling below the predicted
    quantile, which should be close to the quantile itself (e.g. ~25% for the 0.25
    quantile) if the model is well-calibrated. A coverage far off from its target
    means that quantile's predictions shouldn't be trusted as-is.
    """
    train, test, X_train, X_test, y_train, y_test = prepare_quantile_train_test(df)

    quantile_models = {}
    for q in quantiles:
        print(f"\nTuning LightGBM quantile model for q={q}...")
        pinball_scorer = make_scorer(mean_pinball_loss, alpha=q, greater_is_better=False)

        model_tuned = RandomizedSearchCV(
            LGBMRegressor(objective='quantile', alpha=q, random_state=42, n_jobs=-1, verbose=-1),
            LGBM_PARAM_GRID,
            n_iter=10,
            cv=5,
            scoring=pinball_scorer,
            random_state=42,
            verbose=2,
        )
        model_tuned.fit(X_train, y_train)

        print(f"Quantile {q:.2f} Best params: {model_tuned.best_params_}")
        print(f"Quantile {q:.2f} Best pinball loss: {-model_tuned.best_score_:.2f}")

        quantile_models[q] = model_tuned

    save_quantile_models(quantile_models)
    report_quantile_calibration(quantile_models, test, X_test)
    return quantile_models


def compare_models(models, X_test, y_test):
    print("Model Performance Comparison:")
    print("-" * 64)
    for name, model in models.items():
        pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, pred)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        r2 = r2_score(y_test, pred)
        print(f"{name:20} | MAE: {mae:.2f}kg | RMSE: {rmse:.2f}kg | R²: {r2:.3f}")


def compare_xgb_tuning(xgb_baseline, xgb_tuned, X_test, y_test):
    xgb_pred = xgb_baseline.predict(X_test)
    xgb_tuned_pred = xgb_tuned.predict(X_test)

    mae_base = mean_absolute_error(y_test, xgb_pred)
    mae_tuned = mean_absolute_error(y_test, xgb_tuned_pred)
    rmse_tuned = np.sqrt(mean_squared_error(y_test, xgb_tuned_pred))
    r2_tuned = r2_score(y_test, xgb_tuned_pred)

    print("\n" + "=" * 60)
    print("Test Set Comparison:")
    print(f"Original XGB        | MAE: {mae_base:.2f}kg")
    print(f"Tuned XGBoost       | MAE: {mae_tuned:.2f}kg | RMSE: {rmse_tuned:.2f}kg | R²: {r2_tuned:.3f}")


def ensemble_predict(models, X):
    """Simple unweighted average of predictions across the given models."""
    predictions = np.column_stack([model.predict(X) for model in models])
    return predictions.mean(axis=1)


def compare_tuned_ensemble(tuned_models, X_test, y_test, title="Tuned Model + Ensemble Comparison"):
    print("\n" + "=" * 60)
    print(title + ":")
    print("-" * 64)

    for name, model in tuned_models.items():
        pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, pred)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        r2 = r2_score(y_test, pred)
        print(f"{name:20} | MAE: {mae:.2f}kg | RMSE: {rmse:.2f}kg | R²: {r2:.3f}")

    ensemble_pred = ensemble_predict(tuned_models.values(), X_test)
    mae = mean_absolute_error(y_test, ensemble_pred)
    rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))
    r2 = r2_score(y_test, ensemble_pred)
    print(f"{'Ensemble (avg)':20} | MAE: {mae:.2f}kg | RMSE: {rmse:.2f}kg | R²: {r2:.3f}")


def train_all(df):
    """Runs the full training pipeline and returns everything downstream code needs
    (fitted models, tuned models, and the train/test splits with feature columns)."""
    train, test, X_train, X_test, y_train, y_test = prepare_train_test(df)

    models = train_baseline_models(X_train, y_train)
    compare_models(models, X_test, y_test)

    xgb_tuned = tune_xgboost(X_train, y_train)
    compare_xgb_tuning(models['XGBoost'], xgb_tuned, X_test, y_test)

    lgbm_tuned = tune_lightgbm(X_train, y_train)
    catboost_tuned = tune_catboost(X_train, y_train)

    tuned_models = {
        'XGBoost (tuned)': xgb_tuned,
        'LightGBM (tuned)': lgbm_tuned,
        'CatBoost (tuned)': catboost_tuned,
    }
    compare_tuned_ensemble(
        tuned_models, X_test, y_test,
        title="3-Model Ensemble: XGBoost + LightGBM + CatBoost"
    )

    return {
        'train': train,
        'test': test,
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'models': models,
        'xgb_tuned': xgb_tuned,
        'lgbm_tuned': lgbm_tuned,
        'catboost_tuned': catboost_tuned,
    }


if __name__ == '__main__':
    df = pd.read_csv(FEATURES_CSV_PATH)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    train_exact_models = False
    train_quantile_model = True
    tune_quantile_model = False  # the RandomizedSearchCV search instead: ~20-25 min per percentile
    if train_exact_models:
        train_all(df)
    if train_quantile_model:
        if tune_quantile_model:
            tune_lightgbm_quantiles(df)
        else:
            train_lightgbm_quantiles(df)
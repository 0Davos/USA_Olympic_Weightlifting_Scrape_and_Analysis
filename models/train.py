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

FEATURE_COLS = [
    'Bodyweight',
    'Sn#1_missed', 'Sn#2_missed', 'Sn#3_missed',
    'CJ#1_missed', 'CJ#2_missed', 'CJ#3_missed',
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

QUANTILES = [0.25, 0.50, 0.75, 0.99]


def prepare_train_test(df):
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


def tune_lightgbm_quantiles(df):
    """Tunes one LightGBM model per quantile in QUANTILES (25th/50th/75th/99th) via
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
    train, test, X_train, X_test, y_train, y_test = prepare_train_test(df)

    quantile_models = {}
    for q in QUANTILES:
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

    print("\nLightGBM Quantile Models (Tuned) - Calibration Check:")
    print("-" * 64)
    for q, model in quantile_models.items():
        pred = model.predict(X_test)
        coverage = (y_test <= pred).mean()
        print(f"Quantile {q:.2f} | Target coverage: {q:6.1%} | Actual coverage: {coverage:6.1%}")

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
    if train_exact_models: 
        train_all(df)
    if train_quantile_model:
        tune_lightgbm_quantiles(df)
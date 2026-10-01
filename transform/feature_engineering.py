# Feature engineering: meet_results_CLEANED.csv -> meet_results_FEATURES.csv
#
# Builds athlete-history-aware features (rolling/expanding stats) for modeling.
# All features use only data available before the current row's competition date,
# via shift(1)/expanding()/rolling(), to prevent leakage.

import os
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLEANED_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_CLEANED.csv")
FEATURES_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_FEATURES.csv")

MISS_COLS = ['Sn#1_missed', 'Sn#2_missed', 'Sn#3_missed',
             'CJ#1_missed', 'CJ#2_missed', 'CJ#3_missed']

MEN_BINS = [50, 60, 65, 71, 79, 88, 94, 110, 200]
MEN_LABELS = ['<60kg', '60-65kg', '65-71kg', '71-79kg', '79-88kg', '88-94kg', '94-110kg', '+110kg']

WOMEN_BINS = [38, 48, 53, 58, 63, 69, 77, 86, 200]
WOMEN_LABELS = ['<48kg', '48-53kg', '53-58kg', '58-63kg', '63-69kg', '69-77kg', '77-86kg', '+86kg']


def safe_polyfit(y):
    try:
        if len(y) < 2:
            return 0
        # Check if all values are the same (no variance)
        if y.nunique() == 1:
            return 0
        return np.polyfit(range(len(y)), y, 1)[0]
    except (np.linalg.LinAlgError, ValueError):
        return 0


def count_comps_last_180_days(group):
    result = []
    for i, current_date in enumerate(group['Date']):
        if i == 0:
            result.append(0)  # First comp
        else:
            # Count comps in last 180 days (excluding current)
            past_dates = group['Date'].iloc[:i]
            count = ((current_date - past_dates).dt.days <= 180).sum()
            result.append(count)
    return pd.Series(result, index=group.index)


def engineer_features(df_cleaned):
    """Bomb-outs (bombed_out=True, Total=0) are kept in the output but handled in two
    tiers, so a Total=0 never reads as a real performance:
      - Performance-history features (bests, trends, miss rates, last-comp total, ...)
        are computed on non-bomb-out rows only, exactly as if bomb-outs didn't exist.
        A bomb-out row itself gets NaN for these (never trained on), and an athlete's
        next real meet still sees their last real total, not a 0.
      - Attendance features (comp count, days since last comp, ...) are computed over
        every row, since a bomb-out is still a competition the athlete showed up to.
    """
    # Sort by athlete and date first
    df_cleaned = df_cleaned.sort_values(['Name', 'Date']).reset_index(drop=True)

    df_cleaned['Gender Binary'] = df_cleaned['Gender'].map({
        'Men': 0,
        'Women': 1
    })

    valid = add_performance_features(df_cleaned[~df_cleaned['bombed_out']].copy())
    perf_cols = [c for c in valid.columns if c not in df_cleaned.columns]
    df_cleaned = df_cleaned.join(valid[perf_cols])

    df_cleaned = add_attendance_features(df_cleaned)
    df_cleaned = add_segment_features(df_cleaned)

    return df_cleaned


def add_performance_features(df_cleaned):
    # Calculate expanding (cumulative) miss rates - excludes current row
    for col in MISS_COLS:
        # Shift(1) moves everything down by 1, so current row uses only previous data
        # expanding() calculates cumulative mean up to that point
        df_cleaned[f'athlete_avg_{col}'] = (
            df_cleaned.groupby('Name')[col]
            .apply(lambda x: x.shift(1).expanding().mean())
            .reset_index(level=0, drop=True)
        )

    # Best snatch/cj/total before current comp
    df_cleaned['best_snatch_to_date'] = (
        df_cleaned.groupby('Name')['Best Sn']
        .apply(lambda x: x.shift(1).expanding().max())
        .reset_index(level=0, drop=True)
    )

    df_cleaned['best_cj_to_date'] = (
        df_cleaned.groupby('Name')['Best CJ']
        .apply(lambda x: x.shift(1).expanding().max())
        .reset_index(level=0, drop=True)
    )

    df_cleaned['best_total_to_date'] = (
        df_cleaned.groupby('Name')['Total']
        .apply(lambda x: x.shift(1).expanding().max())
        .reset_index(level=0, drop=True)
    )

    # Last competition total
    df_cleaned['Last Comp Total'] = (
        df_cleaned.groupby('Name')['Total']
        .shift(1)
    )

    # Time since best total (in days)
    # First, find the date when athlete achieved their best total to date
    df_cleaned['Date of Best Total'] = (
        df_cleaned.groupby('Name')
        .apply(lambda x: x['Date'].shift(1).where(
            x['Total'].shift(1) == x['Total'].shift(1).expanding().max()
        ).ffill())
        .reset_index(level=0, drop=True)
    )

    df_cleaned['Days Since Best Total'] = (
        (df_cleaned['Date'] - df_cleaned['Date of Best Total']).dt.days
    )

    # Recent performance trend (last 3 comps)
    df_cleaned['total_trend_last_3'] = (
        df_cleaned.groupby('Name')['Total']
        .apply(lambda x: x.shift(1).rolling(3, min_periods=2)
               .apply(safe_polyfit))
        .reset_index(level=0, drop=True)
    )

    # Acceleration (is improvement speeding up or slowing down?)
    df_cleaned['total_acceleration'] = (
        df_cleaned.groupby('Name')['total_trend_last_3']
        .diff()
    )

    # Consecutive improvements
    df_cleaned['improvement_streak'] = (
        df_cleaned.groupby('Name')['Total']
        .apply(lambda x: (x.shift(1) > x.shift(2)).astype(int).rolling(3).sum())
        .reset_index(level=0, drop=True)
    )

    # Ratio (typically 0.78-0.82 for balanced lifters)
    df_cleaned['sn_to_cj_ratio'] = (
        df_cleaned.groupby('Name')['Best Sn'].shift(1) /
        df_cleaned.groupby('Name')['Best CJ'].shift(1)
    )

    # Which lift is improving faster?
    df_cleaned['sn_improvement_last_3'] = (
        df_cleaned.groupby('Name')['Best Sn']
        .apply(lambda x: x.shift(1).rolling(3, min_periods=2)
               .apply(safe_polyfit))
        .reset_index(level=0, drop=True)
    )

    df_cleaned['cj_improvement_last_3'] = (
        df_cleaned.groupby('Name')['Best CJ']
        .apply(lambda x: x.shift(1).rolling(3, min_periods=2)
               .apply(safe_polyfit))
        .reset_index(level=0, drop=True)
    )

    return df_cleaned


def add_attendance_features(df_cleaned):
    # Number of competitions before this one
    df_cleaned['Num Competitions'] = df_cleaned.groupby('Name').cumcount()

    # Time since last competition (in days)
    df_cleaned['Days Since Last Comp'] = (
        df_cleaned.groupby('Name')['Date']
        .diff()
        .dt.days
    )

    # Competition Frequency - simpler and more reliable approach
    df_cleaned['comps_last_180_days'] = (
        df_cleaned.groupby('Name', group_keys=False)
        .apply(count_comps_last_180_days)
    )

    # Average days between competitions
    df_cleaned['avg_days_between_comps'] = (
        df_cleaned.groupby('Name')['Days Since Last Comp']
        .apply(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
        .reset_index(level=0, drop=True)
    )

    # Is this comp unusually soon/late?
    df_cleaned['comp_timing_deviation'] = (
        df_cleaned['Days Since Last Comp'] - df_cleaned['avg_days_between_comps']
    )

    return df_cleaned


def add_segment_features(df):
    # Weight class, assigned separately per gender (different bins)
    df['weight_class'] = None
    men_mask = df['Gender'] == 'Men'
    women_mask = df['Gender'] == 'Women'

    df.loc[men_mask, 'weight_class'] = pd.cut(
        df.loc[men_mask, 'Bodyweight'], bins=MEN_BINS, labels=MEN_LABELS, right=False
    ).astype(object)
    df.loc[women_mask, 'weight_class'] = pd.cut(
        df.loc[women_mask, 'Bodyweight'], bins=WOMEN_BINS, labels=WOMEN_LABELS, right=False
    ).astype(object)

    # Percentile rank of Total within weight class (0-100). Ranked among real
    # performances only - bomb-outs (Total=0) would otherwise pile up at the bottom
    # of every class and shift everyone else's percentile; they get NaN instead.
    real_totals = df['Total'].where(~df['bombed_out'])
    df['performance_percentile'] = (
        real_totals.groupby(df['weight_class']).rank(pct=True) * 100
    )

    return df


if __name__ == '__main__':
    df_cleaned = pd.read_csv(CLEANED_CSV_PATH)
    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')

    df_features = engineer_features(df_cleaned)

    df_features.to_csv(FEATURES_CSV_PATH, index=False)
    print(f"Wrote {len(df_features)} rows with engineered features to {FEATURES_CSV_PATH}")

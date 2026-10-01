# USA Olympic Weightlifting Data - Scrape and Performance Analysis

## Overview

This project builds an end-to-end system that:

1. Scrapes all competition results from the USAW athlete portal using Playwright
2. Stores the data in a CSV file with deduplication logic
3. Engineers 25+ features per competition entry to capture athlete trajectory, lift consistency, and competition history
4. Models athlete performance using Linear Regression, Random Forest, XGBoost, LightGBM, and CatBoost (plus a tuned-model ensemble, and LightGBM quantile models for prediction intervals)
5. Evaluates each model through segmented analysis broken down by performance percentile within weight class to determine any imbalances

## Data Collection — `meet_scraper.py`

### Implementation
This scraper uses Playwright to automate a headless Chromium browser, log into the USAW athlete portal, then navigates to every meet result page across all specified dates.

It:
- Handles USAW's multi-factor authentication, awaits user input
- Paginates through both meet listings and per-meet athlete result tables
- Scrapes 14 fields per row: meet name, date, athlete name, bodyweight, all six lift attempts, best snatch, best C&J, total, and weight class
- Deduplicates on `(Meet, Date, Name, Bodyweight)` before appending new rows to the CSV
- Wraps the full run in a retry loop (up to 5 retries before failure) to handle any network flakiness

### Tech stack
`playwright`, `pandas`

## About the Data
All data is sourced from USA Weightlifting's result portal, which tracks every USAW sanctioned competiton result since 2012.

- Total entries: 282,000
- Fields: Meet name, date, athlete name, bodyweight, snatch attempts (3), clean & jerk attempts (3), best snatch, best C&J, total, weight category, gender, age group

Note: Athletes are only able to be identified by name in this current scraping format, as it contains no unique IDs. Thus, athletes with unique names are grouped together, which is a known limitation. This should not affect general trends found by models.

## Analysis — `EDA.ipynb`

### Data Cleaning

- Removes physiologically impossible outliers (e.g. totals > 5.5 x bodyweight)
- Corrected a known data entry error for one athlete by cross-referencing surrounding meets
- Converted missed lifts (sometimes stored as negatives or zeroes in source data) to `NaN` while preserving miss flags, in case they are useful in modeling
- Bomb-outs (Total = 0) are kept in the cleaned data and flagged with a `bombed_out` column, but excluded from model training and from every performance-history feature — a bomb-out is a different kind of event rather than a weak performance, and would badly skew predictions

### Feature Engineering

25+ features engineered per competition entry, all using only data available before the current meet to prevent data leakage:

| Category | Features |
|---|---|
| Lift consistency | Per-attempt miss flags, cumulative athlete miss rate by attempt |
| Historical bests | Best snatch to date, best C&J to date, best total to date |
| Trajectory | 3-comp rolling trend (slope), acceleration of improvement, improvement streak |
| Lift balance | Snatch-to-C&J ratio, per-lift improvement rates over last 3 comps |
| Competition history | Number of competitions, days since last comp, comp frequency (last 180 days), comp timing deviation |

### Visualizations
- Total vs. bodyweight scatterplot by gender
- Bodyweight and total distributions by gender
- 31-feature correlation heatmap
- Competition entries by year
- Bodyweight vs. total with 50th and 85th percentile curves overlaid by weight class

### Segmented Analysis
Athletes are separated into current (2025) IWF weight categories, then segmented into performance percentiles within their class

| Segment | Size |
|---|---|
| Low (<50th percentile) | 135,710 entries |
| Mid (50th–85th) | 95,155 entries |
| High (85th–100th) | 40,697 entries |

A utility function `get_performance_percentile(bodyweight, total, gender)` calculates any lifter's percentile rank relative to the full historical dataset within their weight class.

### Models
Five regression models (plus a tuned-model ensemble) trained on pre-2024 data, evaluated on 2024+ data (57,714 test entries, bomb-outs excluded):
 
| Model | MAE (kg) | RMSE (kg) | R² |
|---|---|---|---|
| Linear Regression | 16.67 | 24.15 | 0.853 |
| Random Forest | 10.55 | 17.78 | 0.920 |
| XGBoost (baseline) | 10.31 | 17.49 | 0.923 |
| LightGBM (baseline) | 10.37 | 17.54 | 0.923 |
| CatBoost (baseline) | 10.77 | 17.83 | 0.920 |
| XGBoost (tuned) | 10.21 | 17.42 | 0.924 |
| LightGBM (tuned) | 10.21 | 17.42 | 0.924 |
| CatBoost (tuned) | 10.34 | 17.48 | 0.923 |
| **Ensemble (tuned XGBoost + LightGBM + CatBoost)** | **10.18** | **17.36** | **0.924** |

XGBoost, LightGBM, and CatBoost were each tuned with `RandomizedSearchCV` (5-fold cross-validation) across depth, learning rate, estimator count, and model-specific parameters. Averaging the three tuned models gives only a small gain (10.18kg vs 10.21kg for the best single model) — they're highly correlated, so ensembling has limited room to help. Linear Regression's 16.7kg shows most of the signal is non-linear interactions; for context, simply guessing "same total as last meet" scores 8.16kg on returning athletes, where the tuned models reach ~7.1kg.

> **Note (2026-09-30):** this table was re-run after two pipeline changes: a leakage fix (the current meet's own missed-attempt flags were removed from the features, since they're only known after the meet — worth roughly 0.26kg of MAE) and bomb-outs being kept in the data but excluded from training/evaluation. The test set is also larger than in earlier versions (new meets scraped since), so these figures aren't directly comparable to older ones. The Neural Network row was removed — it was dropped from the project (see `docs/findings.md`).

#### Key Finding

Segmented evaluation (tuned XGBoost, by performance percentile within weight class) shows error is highest in the bottom half (MAE 11.58kg) and roughly flat across the 50th–85th (9.04kg) and top 15th (9.26kg) percentiles. Athlete history matters far more than segment: returning athletes are predicted to ~7.1kg MAE versus ~27.8kg for first-time competitors (15% of test entries), who have no prior meet to go on. Note that performance percentile is computed from the actual Total, so these segments are selected on the outcome and the gap partly reflects that. XGBoost, LightGBM, and the ensemble are effectively tied, so no single model is clearly best.

## Overall Key Findings

- **Last comp total to date** was the strongest predictors of current total (correlation: 0.98)
- **Tree-based models clearly outperformed Linear Regression** (~10.2kg vs 16.7kg MAE) — tuned XGBoost and LightGBM tie for best single model at 10.21kg (R² 0.924), with the three-model ensemble just ahead at 10.18kg
- **Prediction accuracy improves with competition history** — athletes with more meets were significantly easier to predict than first-time competitors, confirming that feature engineering compounds with experience (~7.1kg MAE for returning athletes vs ~27.8kg for first-time competitors)
- **Miss rates differ meaningfully by attempt** — first-attempt clean and jerk misses were rarest (10.3%), third-attempt clean and jerk misses most common (43.8%), consistent with competitive attempt selection strategy
- **Elite athletes miss more** — top 15th percentile athletes missed at 29.5% (Snatch) and 32.2% (Clean&Jerk) vs 25.6% and 23.9% (Snatch, Clean&Jerk respectively) for bottom 50th percentile

## Error Analysis
 
**Residuals by Performance Segment (Tuned XGBoost)**
 
![residual boxplot](extra/residual_plot.png)
 
- Error is highest in the bottom 50% (MAE 11.58kg vs ~9kg for the upper segments), and that segment also has a long tail of large negative residuals (actual total far below the prediction)
- Lower percentile athletes show wider residual spread, consistent with sparser feature histories and more variable performance

## Limitations

- Athletes are identified by name only — no unique athlete ID exists in the source data, so athletes with identical names are grouped together
- Age is not available from meet-level scraping
- No access to training data, injury history, or competition strategy
- Feature engineering is biased toward athletes with longer competition histories — newer athletes have sparse or null values for trajectory features
- Bomb-outs (athletes who totaled zero) were excluded and not modeled
- Some weight classes are better represented than others, which may affect percentile accuracy in smaller classes

## Future Work

- Refactor code to auto-update CSV file, instead of database. This would also include implementing GitHub Actions
- Scrape by athlete profile, to gain unique ID's, region, and age, which could lead to many more insights and possibly improved models
- Model probability of "bomb-outs" separately
- Focus modeling on higher percentile of lifters, where it can be more useful
- Host visualizations for coaches and athletes (coming soon)

## Setup
```bash
git clone https://github.com/0Davos/USA_Olympic_Weightlifting_Scrape_and_Analysis.git
pip install -r requirements.txt
playwright install chromium
```
 
Create a `.env` file in the root directory:
```
USAW_EMAIL=your_usaw_email
USAW_PASSWORD=your_usaw_password
```
 
Run the scraper:
```bash
python meet_scraper.py
```
 
To open the analysis notebook:
```bash
jupyter notebook
```
Then move into the EDA folder.

### Optional
To run Neural Network cell, requires python 3.11 or earlier
```bash
pip install tensorflow
```
Then uncomment all lines related to the neural network.


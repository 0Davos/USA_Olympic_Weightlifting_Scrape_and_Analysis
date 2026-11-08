# Findings — USA Olympic Weightlifting Analysis

Extracted from `EDA/EDA.ipynb`'s written analysis sections (2026-08-07).

## Neural Network — Why It Was Dropped

#### MAE Discrepancy, Neural Network Issue

Segment-aware evaluation exposes a significant discrepancy among MAE's for each percentile; getting smaller as the percentile increases. This is heteroskedasticity, and it's clear how it has occured. First, lower percentiles have much higher variability implicitly, as they are likely to vary their totals wildly, either increasing quickly or missing lifts randomly. Along with that, our feature engineering is specifically biased towards athletes that have multiple competitions. This means that our top 15th percentile category will have much more precise information on their % missed lifts, trajectories, etc. and are more stable with changes in total.

The neural network fails upon segmented evaluation, and upon further exploration, it makes sense why. Neural networks are naturally unconstrained -- their outputs are not naturally bounded to what we'd expect total's range to be, so it's possible to get the error we did. Since our code didn't change from our overall model (with a relatively normal MAE result) to our segmented models, the natural cause would be that errors are masked by the full model, and exposed in the segmented models. This is because MAE is mean and not median, allowing a few massive outliers to go unnoticed.

#### Do we change any model? Why?

Out of the four models tested, only the Neural Network could do with some individualized changes. The Linear Regression, RF and XGB all have reasonable guesses, with segments getting more accurate as they increase, something that makes sense as lifters gain stability, and also have more feature engineered columns geared towards them.
While I could change the Neural Network, I elected to leave it. I could bound results, either to general bounds (0-400kg), or more specifically if we have data like their last total (probably would be within 100kg of said last total). I could also create more generalized feature engineering, a better loss function, or dive into the model's heteroskedasticity. But the reason I won't is that this data is tabular and structured, something I assumed would work better for models like Random Forest and XGBoost. Along with that, the tree based models

**Update (2026-08-07):** the Neural Network was ultimately dropped from the pipeline entirely rather than fixed — see `models/train.py`. CatBoost, LightGBM, and ElasticNet are being evaluated as replacement candidates instead.

**Update (2026-11-07):** CatBoost and LightGBM were added; ElasticNet was tried and removed (only a slight gain over Linear Regression). Current results are below and in the README.

## Key Findings

Figures updated 2026-11-07. The original numbers from the notebook are kept at the end of this page as a historical record.

### Dataset
- 329,914 competition entries from January 2012 to November 2026 (including 20,895 bomb-outs), across 9,383 meets and ~68,000 athletes (by name)
- Peak competition year was 2019, with 29,514 total competition entries

### Strongest Predictors of Total
- Last comp total to date was the strongest predictor of current total (Correlation: 0.98)
- Best comp total to date was the second strongest predictor (Correlation: 0.97) along with best snatch to date and best clean and jerk to date (Correlations being 0.96)
- Gender binary and bodyweight showed moderate correlations (0.58, 0.62 respectively)

### Model Performance
Trained on pre-2024 meets, tested on 2024+ meets (57,714 entries, bomb-outs excluded), on the leak-free 24-feature set (2026-09-30 run):
- Tuned XGBoost and tuned LightGBM tie for best single model (MAE 10.21kg, R² 0.924); averaging them with tuned CatBoost gives 10.18kg. The models are highly correlated, so ensembling barely helps.
- Random Forest was close behind (10.55kg).
- Linear Regression reached 16.67kg (R² 0.853): a linear model already explains most of the variance, but the tree models cut its error by about 40%, so the remaining signal is non-linear.
- For returning athletes the tuned models reach ~7.1kg, against 8.16kg for simply guessing "same total as last meet". First-time athletes sit near ~27.8kg, since there is no prior meet to go on.

### Segmented Evaluation
Corrected 2026-11-07 (tuned XGBoost, performance percentile within weight class):
- Bottom 50th percentile: MAE 11.58kg
- 50th–85th percentile: MAE 9.04kg
- Top 15th percentile: MAE 9.26kg
- The gap is modest: the bottom half is about 1.3x harder to predict, and above the 50th percentile error is roughly flat. Performance percentile is computed from the actual Total, so the segments are selected on the outcome and the gap partly reflects that.
- Athlete history matters far more than segment (~7.1kg for returning athletes vs ~27.8kg for first-time ones).

### Miss Rates
Non-bomb-out entries, September 2026 data:
- Overall miss rates: Snatch - 26.8%, Clean & Jerk - 26.2%
- First attempt misses for Clean & Jerk were rarest (10.3%), while Clean & Jerk third attempts were the most frequent (43.9%).
- Full order: CJ1 (10.3%), SN1 (14.2%), CJ2 (24.5%), SN2 (25.2%), SN3 (41.0%), CJ3 (43.9%)
- This is consistent with competitive attempt selection strategies
- Top 15th percentile athletes miss rates: Snatch - 29.6%, Clean & Jerk - 32.2%
- Bottom 50th percentile athletes miss rates: Snatch - 25.7%, Clean & Jerk - 24.0%

## Error Analysis

### Overall Residual Distribution (Tuned XGB)
- As shown in the residual plot (`extra/residual_plot.png`), error is highest in the bottom 50% and roughly flat above it; that segment also has a long tail of large negative residuals (actual total far below the prediction)
- Lower percentile athletes show a wider residual spread, consistent with sparser feature histories and more variable performance

## Limitations and Bias
- Athletes with the same name are merged together (no unique athlete ID in the source data)
- Not able to model on exact age of lifter (only the age group is available)
- Not able to see athlete training, injury, etc.
- Some weight classes are "better" in comparison to top weightlifters of the world, some are not
- Biased information towards athletes who have lifted for longer
- Bomb-outs are excluded from modeling (as of 2026-09-30 they are kept and flagged in the data rather than deleted)

## Future Work
- Prediction model v2: predict the change from the last total instead of the total itself, and add age group, career length and month. A one-off experiment cut the median model's error on returning athletes from 6.88kg to 6.59kg (see `ROADMAP.md`)
- Increase the number of segments (especially higher percentiles)
- Scrape by athlete instead of by meet: unique IDs, plus age and region
- Focus on higher percentiles with modeling
- Model when an athlete's next meet will be, based on their averages
- Model the risk of a bomb-out (bomb-outs are now kept and flagged in the data, so this is possible)
- ~~Create interactive visuals for people to use this information practically~~ Done: [olybound.com](https://olybound.com) (launched November 2026)

## Historical Figures (original notebook, pre-2026-09-30)

Kept as a record only; superseded by the sections above.

- Dataset: roughly 300,000 entries from 2012-2025; peak year 2019 with 27,770 entries (bomb-outs were deleted at the time)
- XGB had a test MAE of 10.02kg; the neural network and random forest scored 10.82kg and 10.61kg; Linear Regression 16.58kg. These predate the leakage fix (the current meet's own missed-attempt flags were features, which cost ~0.26kg of MAE to remove)
- Segmented evaluation reported 52.36kg MAE for the bottom 50th percentile vs 9.76kg for the top 15th (~5.5x). This was wrong: the segment thresholds (0.5/0.85) were compared against a 0-100 scale percentile, so "top 15%" covered nearly the whole test set. Fixed in `models/evaluate.py`
- Miss rates were the same to within 0.1 percentage point

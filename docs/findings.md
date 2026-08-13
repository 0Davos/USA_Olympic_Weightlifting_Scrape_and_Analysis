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

## Key Findings

### Dataset
- Roughly 300,000 total competition entries from 2012-2025
- Peak competition year was 2019, with 27,770 total competition entries

### Strongest Predictors of Total
- Last comp total to date was the strongest predictor of current total (Correlation: 0.98)
- Best comp total to date was the second strongest predictor (Correlation: 0.97) along with best snatch to date and best clean and jerk to date (Correlations being 0.96)
- Gender binary and bodyweight showed moderate correlations (0.58, 0.62 respectively)

### Model Performance
- XGB outperformed all models with a test MAE of 10.02kg.
- The neural network and random forest both performed comparably with XGB (MAE:10.82kg, 10.61kg), but the neural network broke down in segmented evaluation, exposing unbounded predictions
- Linear regression as a baseline model achieved an MAE of 16.58kg, which highlights that the majority of our predictive signals are linear.

> **Note (2026-08-07):** the Neural Network has since been dropped from the pipeline entirely (see above). Its MAE figure here is kept as historical record.

### Segmented Evaluation
- All models showed heteroskedasticity across performance tiers
- Bottom 50th percentile had an MAE of 52.36kg, while the top 15th percentile had an MAE of 9.76kg, roughly 5.5 times more accurate predictions for elite athletes
- Elite athletes have a richer history (which increases the accuracy of engineered features) and are more likely to gradually improve or worsen.

> **Note (2026-08-07):** the segment thresholds used to compute this figure (0.5/0.85, compared against a 0-100 scale `performance_percentile` column) had a scale bug that left "top 15%" effectively covering nearly the entire test set. So these two specific numbers likely don't reflect genuinely isolated percentile bands. Fixed in `models/evaluate.py` going forward — these are kept here as historical record, not current ground truth.

### Miss Rates
- Overall miss rates: Snatch - 26.8%, Clean & Jerk - 26.2%
- First attempt misses for Clean & Jerk were rarest (10.3%), while Clean & Jerk third attempts were the most frequent (43.8%).
- Full order: (CJ1, SN1, CJ2, SN2, SN3, CJ3)
- This is consistent with competitive attempt selection strategies
- Top 15th percentile athletes miss rates: Snatch - 29.5%, Clean & Jerk - 32.2%
- Bottom 50th percentile athletes miss rates: Snatch - 25.6%, Clean & Jerk - 23.9%

## Error Analysis

### Overall Residual Distribution (Tuned XGB)
- As shown in our graph under "Segment Aware Analysis", the model's error shrinks significantly at higher performance percentiles, confirming the heteroskedasticity identified in segmented evaluation
- Along with that, lower percentile athletes show a wider residual spread, consistent with sparser feature histories.

## Limitations and Bias
- Like names are included togther
- Not able to model on age of lifter
- Not able to see athlete training, injury, etc.
- Some weight classes are "better" in comparison to top weightlifters of the world, some are not
- Biased information towards athletes who have lifted for longer
- Removed "bomb outs"

## Future Work
- Increase the number of segments (especially higher percentiles)
- Scrape by athlete instead of by meet, has more individual information, but only slightly (only has age, region as other features)
- Focus on higher percentiles with modeling
- Model when an athlete's next meet will be, based on their averages
- Create interactive visuals for people to use this information practically
- Include "Bomb outs", could have models include risk of failure and work into model, may be difficult but could be an enjoyable challenge

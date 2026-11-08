# Model v2, untuned (kept as a fallback)

The five v2 prediction models as first trained on 2026-11-08 (commit 240f300), with the original
models' settings (`QUANTILE_PARAMS` in `models/train.py`), before the v2 tuning search. Kept at the
user's request in case the tuned models turn out worse.

- `lightgbm_q*.pkl` - the scikit-learn wrappers (joblib), as in `models/saved/`
- `lightgbm_q*.txt` - LightGBM's native text format, as served by the API from `app/api/_models/`

To go back to them: copy the `.txt` files into `app/api/_models/` and the `.pkl` files into
`models/saved/` (or retrain with `train_lightgbm_quantiles` in `models/train.py`, which gives the same
models). Test-set results: median error 6.58kg, coverage 1.1/26.3/50.9/76.0/98.9%, elite (best 330kg+)
99th-percentile coverage 96.8%.

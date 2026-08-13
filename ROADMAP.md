# Roadmap — USA Olympic Weightlifting Scrape & Analysis

Working task list, refined 2026-08-06. Ordered: Phase 1 (pipeline/modeling) is meant to land before Phase 2 (website) starts, since the website features depend on clean, incrementally-updated data.

Do not start any item here without confirming scope in chat first — see `CLAUDE.md`.

## Phase 1 — Pipeline & Modeling Refactor

- [x] **Scraper: append instead of overwrite.** `meet_scraper.py` now appends new rows to `data/meet_results.csv`, deduped on `(Meet, Name, Bodyweight)` against existing rows, instead of regenerating the file each run. Supabase removed entirely — project is CSV-only.
- [x] **Cleaner + feature engineering: own files.** `transform/meet_clean.py` now combines Weight Category parsing with the notebook's outlier/miss cleaning (the two hardcoded-index data fixes rewritten as content-based matches so they survive future appends). `transform/feature_engineering.py` extracts the notebook's 24 leakage-safe rolling/expanding features, plus `weight_class`/`performance_percentile` (added later, once `models/evaluate.py` needed them too — single source of truth instead of duplicated logic). Revised from the original "append-based" plan to a full rebuild each run instead — feature engineering needs each athlete's complete history to compute correctly, and a full recompute over ~282K rows is cheap enough (cleaning: seconds; feature engineering: ~12 min, dominated by per-athlete rolling calculations). Verified against real data.
- [x] **Modeling: extract to its own files.** `models/train.py` (Linear Regression, Random Forest, XGBoost baseline + tuned) and `models/evaluate.py` (segment-aware MAE breakdown + residual plot). Neural Network dropped entirely rather than extracted — see `docs/findings.md` for the historical reasoning, `CLAUDE.md` for current model status. Found and fixed a real bug while extracting `evaluate.py`: the notebook compared a 0-100 scale `performance_percentile` against 0.5/0.85 thresholds, so "top 15%" covered nearly the whole test set — corrected to 50/85. Both files verified against real data (results in `CLAUDE.md`). `EDA.ipynb` now ends after the segmented-analysis-setup section; all modeling/evaluation/write-up cells removed.
- [x] **Add models:** CatBoost and LightGBM added to `models/train.py` (baseline + tuned, matching the existing XGBoost `RandomizedSearchCV` pattern). ElasticNet was also added and tested (including with `StandardScaler`, since it's the one model in the lineup actually sensitive to feature scale) but only showed a slight improvement, nowhere near the tree-based models' ~10kg MAE range — both ElasticNet and the scaling step were removed rather than carry the added complexity for a model unlikely to be used. Ensembling the three tuned tree models (XGBoost + LightGBM + CatBoost) gave a small improvement (10.01kg vs XGBoost alone at 10.04kg) — the models are correlated enough that ensembling has limited room to help. A follow-up XGBoost + Random Forest ensemble (testing whether a structurally different model adds more diversity) came out worse (10.15kg) and was removed.
- [x] **Notes/documentation: own file.** `docs/findings.md` — Key Findings, Error Analysis, Limitations and Bias, Future Work, plus the Neural Network post-mortem, moved verbatim from the notebook. Two dated caveat notes added where figures were affected by the NN removal / segment-threshold bug. User is doing a manual editing pass over this and the README before pushing to GitHub.
- [ ] **GitHub Actions — cleaner.** Run the cleaner automatically once new raw data is pushed.
- [ ] **GitHub Actions — scraper (blocked/open investigation).** USAW's portal requires a 2FA code delivered by email/SMS each login — there's no way to generate that code programmatically, so full unattended automation isn't currently possible. Two paths, undecided:
  - Keep the scraper manual/local only (default/safe assumption for now).
  - Investigate whether USAW's login supports a "remember this device" session that outlives a single login — if so, a saved session/cookie could be stored as a GitHub secret and reused in Actions until it expires, needing periodic manual refresh. Unverified — needs someone to actually check the login flow before this is a real option.

## Phase 2 — Website

**Stack: not decided — open question.** Candidates to weigh when we get here: Streamlit/Dash (fast, Python-only) vs. a full separate frontend + API backend.

Features (chunked out from "website idea"):

- [ ] **Athlete lookup** — search/view a specific athlete's history.
- [ ] **Meet lookup** — search/view a specific meet's results.
- [ ] **Graph of specific athletes** — performance over time for a chosen athlete.
- [ ] **Confidence intervals (25/50/75/99) of future performance** — projected performance bands, with checkboxes to toggle each band on/off. Open question: exclude bomb-outs from this projection, or include them? **Modeling groundwork done:** `models/train.py`'s `tune_lightgbm_quantiles()` trains and tunes 4 LightGBM quantile models (one per quantile, `RandomizedSearchCV` scored on pinball loss at each quantile's specific `alpha` — not MAE, which would optimize for the wrong objective for anything but the median), with an empirical coverage/calibration check printed after training, and saves all 4 to `models/saved/` via `joblib` so they don't need retraining to reuse. Still open: the website UI itself, and whether to extend beyond LightGBM-only — an XGBoost+CatBoost quantile ensemble was discussed but deprioritized, since the same correlated-models dynamic that capped point-prediction ensembling gains (see above) likely applies here too.
- [ ] **"Bomb out" rates and prediction** — historical bomb-out rate stats plus a predictive model for bomb-out likelihood.
- [ ] **Graph overlap for two athletes** — compare two athletes, either overlaid on one graph or side-by-side.
- [ ] **A-standards integration** — incorporate IWF/USAW "A standard" qualifying totals so the site can show, live, the best men's and women's athletes and their % to that standard.

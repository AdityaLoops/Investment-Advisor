# Investment Advisor Tool (Robo-Advisor Calculator)

**Project for:** Anand Rathi Internship
**Goal:** Given a principal amount (₹X), an investment horizon (Y years), and a risk tolerance, recommend the fund expected to give the best risk-adjusted outcome — and project what the investment will grow to.

This is **not** a stock/price predictor. It does not attempt to forecast future NAV values. It uses historical fund performance to answer a practical advisory question: *"Given my money, my timeline, and my risk appetite, which of these funds should I choose?"*

---

## Project Structure

```
investment_advisor_project/
├── Data/
│   ├── raw/           # Raw NAV history per fund (from Phase 1)
│   └── processed/     # Derived datasets (rolling CAGR, risk tables)
├── Notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_baseline_calculator.ipynb
│   ├── 03_eda_feature_engineering.ipynb
│   └── 04_modeling.ipynb
├── Rates/
└── src/
    └── calculators.py  # Reusable functions: compound_interest(), recommend_best(),
                         # recommend_fund(), advise_investment()
```

## Funds Covered

| Fund | Code | Category |
|---|---|---|
| HDFC Large Cap | 119018 | Equity |
| HDFC Corporate Bond | 118987 | Debt |
| HDFC Hybrid Equity | 119062 | Hybrid |
| SBI Large Cap | 119598 | Equity |
| ICICI Large Cap | 120586 | Equity |
| ICICI Corporate Bond | 120692 | Debt |

---

## Phase 1: Data Collection

Pulled historical NAV data for all 6 funds using `mftool`, covering **2013 to July 2026** (~3,266–3,338 rows per fund). Saved as individual CSVs in `Data/raw/`. This is the single source of truth all later phases build on — no external or synthetic data was introduced.

---

## Phase 2: Baseline Calculator (No ML)

Built a straightforward compound interest calculator using the standard formula:

```
A = P(1 + r)^t
```

Implemented as `compound_interest(p, r, t)` and `recommend_best()` in `src/calculators.py`.

**Key finding:** using a single static, guessed rate per fund, the "best fund" ranking never changes regardless of years or principal invested — the model can't differentiate by input, since a static rate carries no information about time or risk. This limitation directly motivated everything that followed.

---

## Phase 3: EDA & Feature Engineering

Moved from guessed rates to **real historical returns**:

- `calculate_cagr()` — computes actual Compound Annual Growth Rate from NAV data
- `calculate_rolling_cagr()` — computes CAGR across every possible rolling window, for `window_years` 1–10, using actual calendar dates (`pd.DateOffset` + `.searchsorted()`, not naive trading-day row offsets, after catching and fixing a bug where the two were conflated)

**Key findings:**
- Switching from guessed to real rates flipped the "best fund" from Phase 2's `sbi_large_cap` to `icici_large_cap`
- Equity funds show dramatically reduced worst-case risk at longer holding periods (e.g. `hdfc_large_cap`: -37% worst case at 1 year, never negative at 7+ years)
- `icici_large_cap` was consistently a top/near-top performer with comparatively low equity volatility
- A "dip then recovery" pattern appeared in mean CAGR across window lengths — noted but not fully explained at the time
- Corporate bond funds stayed flat and low-risk regardless of horizon

**Known limitations:** 13.5-year dataset does not include a major market crash within the data window in a way that stresses all horizons equally; small fund sample (6 funds, 2 fund houses' worth of categories).

---

## Phase 4: Modeling

### 4a — Baseline: Linear Regression

Restructured data into `long_df` (117,804 rows — every individual rolling-window CAGR as its own row), one-hot encoded by fund, split **80/20 by `start_date`** (time-based, not random — random shuffling would leak near-duplicate overlapping windows between train and test).

**Result:** MAE 0.0567, R² 0.174.

**Why it underperformed:** the `window_years` coefficient came out near-zero (-0.00077), meaning the model learned that holding period barely affects predicted *mean* CAGR. This contradicted the risk pattern found in Phase 3, and traces back to a real limitation — Linear Regression cannot represent **interaction effects** (e.g. "equity is worse short-term, better long-term" behaving differently per fund) without those interactions being manually engineered in.

**Practical consequence:** the model would recommend nearly the same 1–2 funds regardless of the number of years entered — defeating the purpose of a horizon-sensitive advisor tool.

### 4b — Random Forest Regressor

Same features, same split, `RandomForestRegressor(n_estimators=100, random_state=42)`.

**Result:** MAE 0.0589, R² 0.164 — essentially the same as, or marginally worse than, Linear Regression.

**Why added flexibility didn't help:** with only `window_years` (10 values) × `fund` (6 values), there are just **60 unique feature combinations** underlying all 117,804 rows. Both models converge toward learning the per-bucket average CAGR; there wasn't meaningfully more signal in the *mean* return for a non-linear model to extract. This result was documented as an informative negative finding, not a failure: it confirmed the bottleneck was the feature set and the target (mean CAGR), not model choice.

### 4c — Risk-Adjusted Scoring (the approach that worked)

**Reframe:** rather than predicting mean CAGR (which barely varies with horizon), use the fact that **worst-case CAGR varies dramatically with horizon** — equity funds' downside risk shrinks fast as `window_years` increases, while bond funds' risk stays flat throughout. This is real signal already present in the Phase 3 data, requiring no new data collection.

Built `risk_return_df` (60 rows: one per fund × window_years combination) with `mean` and `min` CAGR per group, then a risk-adjusted score:

```
score = mean_cagr - (penalty_weight × max(-min_cagr, 0))
```

`penalty_weight` represents **risk tolerance**: higher values penalize downside risk more heavily (conservative), lower values favor raw expected return (aggressive).

**Validation:** tested `penalty_weight` from 0.2 to 2.0 — the recommended fund shifts predictably and monotonically from equity to bonds as risk-aversion increases, and the horizon at which equity "takes over" extends further out at higher penalty weights:

| penalty_weight | Bonds win at years... | Equity takes over at year... |
|---|---|---|
| 0.2 | none | 1 |
| 0.5 | 1 | 2 |
| 1.0 | 1, 2 | 3 |
| 2.0 | 1, 2, 3 | 4 |

This resolved the core concern raised during development: that the tool's recommendation would stagnate regardless of input. It now differentiates meaningfully across **two real user-facing inputs** — investment horizon and risk tolerance — grounded in actual historical risk data.

### 4d — End-to-End Pipeline

`advise_investment(risk_return_df, principal, years, penalty)` in `src/calculators.py` chains the full pipeline:

1. `recommend_fund()` — finds the best fund and its historical mean CAGR for the given horizon and risk tolerance (includes input validation: rejects `penalty` outside `[0, 2]` with a clear message rather than crashing)
2. `compound_interest()` — projects the final ₹ value using that fund's rate (reuses the Phase 2 function directly)

**Example:**
```python
advise_investment(risk_return_df, 50000, 5, 0.5)
```
→ Recommends `icici_large_cap` (expected CAGR 15.46%, worst-case ~0%), projecting ₹50,000 to ≈₹1,02,603.10 over 5 years.

This closes the loop from raw data (Phase 1) to a working, evidence-based recommendation with a concrete ₹ projection (Phase 4) — the original project goal, fully implemented.

---

## Phase 5: ML-Driven Risk Estimation — Quantile Regression

**Motivation:** Phase 4c's `recommend_fund()` used a hand-computed historical minimum (`min_cagr`) as its risk measure — accurate, but entirely rule-based, with no trained model in the recommendation path itself. This phase replaces that hand-computed number with a genuinely trained ML model.

**Why not just regress on mean CAGR again:** Phase 4a/4b already showed mean CAGR barely varies with `window_years`, which is why those models underperformed. The real learnable signal is in *risk*, not average return — risk shrinks with holding period in a way that varies meaningfully by fund, exactly what Phase 3 and Phase 4c's `min_cagr` table already demonstrated.

**Approach:** trained `GradientBoostingRegressor(loss='quantile', alpha=...)` on row-level `long_df` (same features as before). Quantile regression predicts a specific low percentile of the CAGR distribution — e.g. "the value this fund/horizon falls below only 5% of the time" — a statistically robust analogue to a historical worst-case.

**Alpha tuning:**

| alpha | Behavior |
|---|---|
| 0.1 | Reasonable, but noticeably less pessimistic than actual historical `min` at short horizons |
| **0.05** | **Closer to historical `min`, while staying smooth and monotonic — best balance, used as final model** |
| 0.01 | Closer still on average, but noisy — non-monotonic across adjacent `window_years`, and at least one case predicting worse than the fund's actual all-time worst case (overfitting to a thin, correlated sample) |

**Integration:** `recommend_fund()` and `advise_investment()` extended with a `risk_column` parameter (default `'min'`, backward compatible), so either the historical risk measure or the ML-predicted one (`predicted_min_cagr`, in `ml_risk_df`) can be used interchangeably in the same scoring formula.

**Validation:** across multiple (`window_years`, `penalty`) test cases, the historical and ML-based risk measures **always agreed on which fund to recommend**. They differed in severity — the historical minimum, being a single extreme outlier, applies a harsher penalty at short horizons than the smoother ML estimate. E.g. at `window_years=3`, `penalty=1.0`: same recommended fund (`icici_large_cap`), but score 0.106 (historical) vs. 0.158 (ML) — because the ML model's 5th-percentile estimate wasn't negative while the single worst historical window was.

**Conclusion:** the ML model validates the original hand-built approach rather than contradicting it, while offering a more statistically grounded, less outlier-sensitive risk estimate. The recommendation engine now has a genuinely trained model in the loop, with tuned hyperparameters and cross-validated behavior against the original rule-based approach — not just descriptive statistics.

---

## Core Functions Reference (`src/calculators.py`)

| Function | Purpose |
|---|---|
| `compound_interest(p, r, t)` | Projects final value using compound interest |
| `recommend_best(...)` | Phase 2 baseline recommender (static rates) |
| `recommend_fund(risk_return_df, years, penalty, risk_column='min')` | Risk-adjusted fund recommendation; works with either historical (`min`) or ML-predicted (`predicted_min_cagr`) risk measures |
| `advise_investment(risk_return_df, principal, years, penalty, risk_column='min')` | Full pipeline: recommendation → ₹ projection, same risk_column flexibility |

---

## Known Limitations

- **13.5-year dataset**: does not include a market crash stressing all horizons equally; longer-window (7–10yr) CAGR figures are drawn from fewer independent historical periods than shorter windows, since windows overlap heavily
- **Small fund sample**: 6 funds across 3 categories (equity, hybrid, debt) — not representative of the full fund universe
- **Dummy variable trap** in the Phase 4a/4b encoding (all 6 fund columns kept, none dropped as baseline) — doesn't affect the risk-adjusted approach, but noted for any future regression work
- **Overlapping rolling windows**: adjacent windows share most of their underlying dates, so the 117,804 "rows" represent far fewer truly independent scenarios (~60 unique fund/horizon buckets, each estimated from a heavily autocorrelated sample) — this was the main reason the regression approach (4a/4b) struggled, and why the split was done by time rather than randomly
- **No purge gap at the train/test boundary**: windows immediately adjacent to the split cutoff date can still leak similar information across train/test, even with a time-based split. Deferred as a future refinement rather than blocking initial modeling

---

## Future Extensions (Phase 2 of the project)

- **Market-conditions feature**: incorporate a trailing market-return indicator (e.g. average return across all 6 funds in the N months prior to a window's `start_date`) computed from existing NAV data — no new data collection required
- **More funds / more data**: expand beyond 6 funds and/or pull a longer NAV history if available, to reduce the "small independent sample" limitation and better represent market downturns
- **Natural-language query input**: let a user type something like "I have ₹50,000 for 5 years, low risk" and have the tool parse `principal`, `years`, and risk tolerance automatically. Lightweight option: regex-based number/keyword extraction. Stretch goal: full NLP parsing
- **Purge gap in the train/test split**: add a buffer around the time-based cutoff to fully eliminate boundary leakage between overlapping windows, once there's enough data to afford the loss
- **Risk-tolerance UI**: expose `penalty_weight` as a simple user-facing choice (e.g. Conservative / Moderate / Aggressive → mapped to weight values) rather than a raw numeric input

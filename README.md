# Investment Advisor Tool (Robo-Advisor Calculator)

**Project for:** Anand Rathi Internship
**Goal:** Given a principal amount (₹X), an investment horizon (Y years), and a risk tolerance, recommend the fund expected to give the best risk-adjusted outcome — and project what the investment will grow to.

**Live demo:** https://investment-advisor-d89n.onrender.com/
*(Free-tier hosting — the app sleeps after 15 minutes of inactivity; the first request after a while can take 30–60 seconds to wake up.)*

This is **not** a stock/price predictor. It does not attempt to forecast future NAV values. It uses historical fund performance to answer a practical advisory question: *"Given my money, my timeline, and my risk appetite, which of these funds should I choose?"*

> **A note on "expected" figures:** all CAGR/return figures in this tool are computed from real historical NAV data. They describe what actually happened in the past, not a forecast of the future. Past performance is not indicative of future returns — this is true of any tool like this, not a caveat specific to this project.

## ✨ Web Application Features

### 🔐 User Authentication

- User Registration
- Secure Login & Logout
- Password Hashing using Werkzeug
- Session-based Authentication
- Protected Routes

### 📜 Search History

- Automatically saves every investment search
- View previous searches
- One-click **Run Again** functionality
- Users can only access their own search history

### 🤖 Recommendation Engine

- AI-powered mutual fund recommendations
- Historical & AI-predicted risk estimation
- Adjustable risk tolerance
- Configurable number of recommendations
- Balanced / Best-case / Conservative projections

### 🎨 User Interface

- Modern dark-themed interface
- Responsive recommendation cards
- Improved navigation

---

## Project Structure

```
investment_advisor_project/
├── Data/
│   ├── raw/            # Original 6-fund NAV history (Phase 1, via mftool)
│   └── external/        # 140/138-fund dataset + all derived checkpoints
│       ├── final_selection_140funds.csv
│       ├── nav_selected_140funds.csv
│       ├── results_df_138funds.csv
│       ├── results_df_138funds_with_predictions.csv
│       └── risk_return_df_138funds_filtered_min7yr.csv   # <- final dataset the web app runs on
├── Notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_baseline_calculator.ipynb
│   ├── 03_eda_feature_engineering.ipynb      # Phase 3 (6-fund EDA)
│   ├── 04_modeling_risk_scoring.ipynb        # Phase 4/5 (6-fund modeling)
│   ├── 05_expanded_dataset_pipeline.ipynb    # Phase 6 (138-fund pipeline, self-contained)
│   ├── 06_recommendations.ipynb              # Loads final checkpoint, runs recommendations
│   └── archive/
│       └── 03_raw_working_notebook_pre_cleanup.ipynb   # Full unedited working history —
│                                                         # kept for transparency into the actual
│                                                         # debugging process (bugs found, dead
│                                                         # ends, live methodology decisions)
├── src/
│   └── calculators.py     # compound_interest(), recommend_best(), recommend_fund(),
│                           # advise_investment(), advise_investment_web()
└── web/
    ├── app.py
    ├── database.py
    ├── models.py
    ├── templates/
    │   ├── index.html
    │   ├── login.html
    │   ├── register.html
    │   └── history.html
    ├── static/
    │   └── style.css
    └── requirements.txt
```

---

## Original 6 Funds (Phases 1–5)

| Fund | Code | Category |
|---|---|---|
| HDFC Large Cap | 119018 | Equity |
| HDFC Corporate Bond | 118987 | Debt |
| HDFC Hybrid Equity | 119062 | Hybrid |
| SBI Large Cap | 119598 | Equity |
| ICICI Large Cap | 120586 | Equity |
| ICICI Corporate Bond | 120692 | Debt |

Phases 1–5 (below) were built and validated on these 6 hand-picked funds before the project scaled up in Phase 6 to a genuinely diverse 138-fund universe.

---

## Phase 1: Data Collection

Pulled historical NAV data for all 6 funds using `mftool`, covering **2013 to July 2026** (~3,266–3,338 rows per fund). Saved as individual CSVs in `Data/raw/`. This is the single source of truth all later phases build on — no external or synthetic data was introduced at this stage.

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
- Corporate bond funds stayed flat and low-risk regardless of horizon

---

## Phase 4: Modeling (6 Funds)

### 4a — Baseline: Linear Regression

Restructured data into `long_df` (117,804 rows — every individual rolling-window CAGR as its own row), one-hot encoded by fund, split **80/20 by `start_date`** (time-based, not random — random shuffling would leak near-duplicate overlapping windows between train and test).

**Result:** MAE 0.0567, R² 0.174. The `window_years` coefficient came out near-zero, meaning the model learned that holding period barely affects predicted *mean* CAGR — an informative negative result, not a failure.

### 4b — Random Forest Regressor

Same features, same split. **Result:** MAE 0.0589, R² 0.164 — essentially unchanged from Linear Regression. With only 60 unique `(window_years, fund)` combinations underlying 117,804 rows, both models converged toward the same per-bucket average — confirming the bottleneck was the feature set and target (mean CAGR), not model choice.

### 4c — Risk-Adjusted Scoring (the approach that worked)

**Reframe:** worst-case CAGR varies dramatically with horizon — equity funds' downside risk shrinks fast as `window_years` increases, while bond funds' risk stays flat. Built `risk_return_df` with a risk-adjusted score:

```
score = mean_cagr - (penalty × max(-min_cagr, 0))
```

`penalty` represents risk tolerance (0–2): higher values penalize downside risk more heavily. Validated that different penalty values produce genuinely different, sensible recommendations — a monotonic equity→bonds crossover as risk-aversion increases.

### 4d — End-to-End Pipeline

`advise_investment(risk_return_df, principal, years, penalty)` chains `recommend_fund()` → `compound_interest()`, closing the loop from raw data to a working, evidence-based ₹ projection.

---

## Phase 5: ML-Driven Risk Estimation — Quantile Regression (6 Funds)

**Motivation:** replace the hand-computed historical minimum (`min_cagr`) risk measure with a genuinely trained model.

**Approach:** `GradientBoostingRegressor(loss='quantile', alpha=0.05)` trained on row-level `long_df`, predicting the 5th percentile of the CAGR distribution as `predicted_min_cagr`.

**Alpha tuning:** tested 0.1 / 0.05 / 0.01 — **0.05 chosen** as the best balance between tracking the historical minimum and staying smooth/monotonic across window lengths.

**Validation:** historical and ML-based risk measures **always agreed on which fund to recommend**, differing mainly in severity, not direction — evidence the model learned something real rather than noise.

`recommend_fund()` / `advise_investment()` extended with a `risk_column` parameter (`'min'` or `'predicted_min_cagr'`), so either risk measure can drive the scoring formula interchangeably.

---

## Phase 6: Scaling to 138 Funds

### Motivation

Everything above covered only 6 hand-picked funds. This phase scales the same recommendation engine to a much larger, genuinely diverse fund universe — while deliberately avoiding cherry-picking funds to produce "interesting" results.

### Data source

Switched to a daily-updated, AMFI-derived dataset (GitHub: `InertExpert2911/Mutual_Fund_Data`). Validated against the original mftool data before trusting it — spot-checked `icici_large_cap`'s NAV values on shared dates and found an exact match.

### Fund selection

- Filtered scheme metadata to Direct + Growth plans only (via `Scheme_NAV_Name` string matching), excluding dividend/IDCW variants
- Mapped 73 raw, inconsistently-named AMFI categories down to 7 target categories: large-cap, mid-cap, small-cap, corporate bond, short-duration debt, hybrid, index
- Sampled ~20 funds per category for genuine diversity — not selected to produce a particular outcome

### Category-based encoding (avoiding sparsity)

One-hot encoding 138 individual funds (as done at 6-fund scale) would create ~138 sparse feature columns with too few supporting rows each. Instead, the ML model encodes `Scheme_Category` (7 columns) as its feature, while final recommendation scoring still uses each fund's own real historical mean/min — so recommendations stay fund-specific even though the model only sees category-level information.

**Known limitation:** because the quantile model has no fund-level feature, `predicted_min_cagr` gives an *identical* value to every fund in the same category at the same `window_years`. Historical `min_cagr` remains the fund-specific risk measure and is the more reliable choice for differentiating between funds in the same category. A possible future improvement: add each fund's own historical `mean_cagr` as a single numeric feature (not one-hot) to differentiate within a category without reintroducing sparsity.

### Data-quality bugs found and fixed

1. **Two funds (Scheme_Code 148265, 148313) had `NAV = 0.0` for every single row** — no salvageable data. Dropped entirely, reducing the working set from 140 selected funds to 138.
2. **Invesco India Short Duration Fund (Scheme_Code 120560) had a corrupted NAV value on 2013-04-22** that inflated its scale by roughly 100x from that date onward (likely a decimal/unit error at the data source). This produced a fabricated ~257% single-year CAGR that surfaced during recommendation testing. Traced to the exact date via day-over-day percent-change analysis; fixed by dropping the pre-2013-04-22 segment and recomputing CAGR/risk figures on the corrected, internally-consistent data.

### Short-history bias — found and fixed

While testing recommendations, some 5-year projections looked implausibly high (~30%+ CAGR). Investigation found: **46% of the 138 funds (63/138) have NAV history starting only after 2018**, meaning their rolling-window CAGR figures are computed entirely within the 2019–2024 period — an unusually strong stretch for Indian equities (COVID recovery + broader bull run). This inflated both `mean_cagr` and `min_cagr` for these funds relative to what a full market cycle would show.

**Fix:** added a filter (`starts_before_2018`) requiring a fund's NAV history to reach back before 2018 before it's eligible for recommendation. This is a data-availability gate, not a statistical adjustment — it removes funds that structurally cannot have a trustworthy multi-year track record, rather than shrinking numbers for funds that remain in the pool. Verified the fix: after filtering, top recommendations still showed strong (~20–25% CAGR) but now genuinely multi-cycle-verified results, confirmed by inspecting individual funds' rolling-CAGR history across a full 2013–2021 span (dips, recoveries, and a real range — not an artifact of a narrow bull-run sample).

### Range-based output (instead of a single number)

Originally, `advise_investment()` projected only one value, based on `mean_cagr` — which reads like a confident promise rather than a historical summary. Updated to show three figures per recommended fund:

- **Balanced estimate** — average of the best-case and worst-case *projected rupee amounts* (not CAGRs, since CAGR compounding is exponential — averaging final amounts is the correct way to blend two compounded outcomes)
- **Best case** — projected value using historical `mean` CAGR
- **Worst case** — projected value using the selected risk measure (`min` or `predicted_min_cagr`)

### Known limitation: risk penalty has diminishing effect at longer horizons

In the filtered (post-2018-history) dataset, most funds' worst-case (`min`) CAGR turns positive by mid-length windows — consistent with the core Phase 3 finding that downside risk shrinks with holding period. This means the risk penalty slider has less to act on at `window_years=10` than at `window_years=1`, since there's less negative downside left to penalize at longer horizons. Not a bug — a restatement of the project's own core finding showing up again in the recommendation layer — but worth knowing when interpreting long-horizon results.

---

## Web Application

The project includes a Flask web application that allows users to:

- Register an account
- Securely log in
- Generate personalized investment recommendations
- Save searches automatically
- View previous investment searches
- Instantly rerun previous recommendations
- Choose between historical and AI-predicted risk estimation
- Select the number of recommendations returned

The application uses SQLite for authentication and persistent search history while loading the recommendation dataset into memory during startup for fast inference.

**Live at:** https://investment-advisor-d89n.onrender.com/

Deployed on Render's free tier.

**Labeling note:** the UI distinguishes between historically-derived figures (real past averages/worst-cases — no ML involved) and the genuinely AI-predicted figure (`predicted_min_cagr`, from the quantile regression model), since conflating the two would misrepresent which numbers are actually model output versus plain arithmetic on historical data.

---

## Database

SQLite is used for lightweight persistent storage.

The application stores:

- Registered users
- Secure password hashes
- Search history
- Investment parameters required to rerun previous recommendations

The database is automatically created on first launch.

---

## Authentication

Authentication includes:

- Password hashing using Werkzeug
- Flask session management
- Protected routes
- Authorization checks preventing users from accessing another user's search history

---

## Screenshots

### Home Page

<img width="2793" height="1567" alt="image" src="https://github.com/user-attachments/assets/83e63ac5-1592-4209-b951-e3fa596d105d" />


### Recommendation Results

*(Add Screenshot)*

### Search History

*(Add Screenshot)*

### Login

*(Add Screenshot)*

---

## Core Functions Reference (`src/calculators.py`)

| Function | Purpose |
|---|---|
| `compound_interest(p, r, t)` | Projects final value using compound interest |
| `recommend_best(...)` | Phase 2 baseline recommender (static rates) |
| `recommend_fund(risk_return_df, years, penalty, risk_column='min', n=1)` | Risk-adjusted fund recommendation; supports historical (`min`) or ML-predicted (`predicted_min_cagr`) risk, and top-N results |
| `advise_investment(risk_return_df, principal, years, penalty, risk_column='min', n=1)` | Full pipeline: recommendation → balanced/best-case/worst-case ₹ projections (printed) |
| `advise_investment_web(risk_return_df, principal, years, penalty, risk_column='min', n=1)` | Same as above, returned as structured data for the Flask frontend |

---

## Known Limitations (Full List)

- **`predicted_min_cagr` is category-level, not fund-level** — every fund in the same category at the same `window_years` receives an identical ML-predicted risk value. Use historical `min` for fund-specific risk differentiation.
- **Risk penalty has diminishing effect at longer horizons** in the filtered 138-fund dataset, since most funds' worst-case CAGR turns positive by mid-length windows.
- **Short-history funds are excluded from recommendations** (any fund whose NAV history starts after 2018) — this shrinks the effective candidate pool but was necessary to avoid systematically inflated figures for newer funds.
- **13.5-year original dataset (6 funds)** does not include a market crash stressing all horizons equally; longer-window (7–10yr) CAGR figures are drawn from fewer independent historical periods than shorter windows, since windows overlap heavily.
- **Overlapping rolling windows**: adjacent windows share most of their underlying dates, so row counts overstate the number of truly independent scenarios — this was the main reason the Phase 4a/4b regression approach struggled, and why train/test splits are done by time, not randomly.
- **No purge gap at the train/test boundary** — windows immediately adjacent to the split cutoff date can still share information across train/test, even with a time-based split. Deferred as a future refinement.
- **All figures are historical, not predictive** — "expected"/"balanced"/"best-case" labels describe what a fund's real past rolling-window performance looked like, not a forecast. This is stated explicitly in the app UI and should be treated as a hard limitation of any tool built this way, not specific to this project.
- **Free-tier hosting** — the live demo sleeps after 15 minutes of inactivity; first request afterward takes 30–60 seconds.

---

## Future Extensions

- **Fund-level feature in the quantile model** — add each fund's own historical `mean_cagr` as a numeric feature to differentiate `predicted_min_cagr` within a category, without reintroducing per-fund sparsity
- **Market-conditions feature** — trailing market-return indicator, computed from existing NAV data, no new collection required (explored in depth, deferred: likely shifts the equity/bond boundary more than it changes which specific equity fund wins)
- **Naive-average baseline in the output** — surface the `penalty=0` (pure historical average, no risk adjustment) pick alongside the risk-adjusted recommendation, for direct comparison
- **Purge gap in the train/test split** — eliminate residual boundary leakage between overlapping windows once there's enough data to afford the loss
- **Benchmark comparison in the UI** — show a recommended fund's historical CAGR next to a reference point (e.g. "broad equity mutual funds have historically averaged 12–15% CAGR") so users can immediately see when a pick is an exceptional historical performer rather than a typical one
- **Email OTP Verification**
- **Password Reset**
- **User Dashboard**
- **Favorite Searches**

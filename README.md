# RetainAI: Retail Broking Retention Console

## What It Is
RetainAI is an early intervention and retention intelligence console built for retail broking platforms. It predicts which newly onboarded retail investors are likely to become dormant, diagnoses the behavioral drivers behind their drop-off using only their first 14 days of app activity, and prescribes targeted, positive-ROI interventions.

## The Core Product Question
> **"Which new investors will go dormant between Day 61 and Day 90 after signup, why are they disengaging, and what specific intervention can we deploy on Day 14 that delivers a positive net expected return?"**

In retail investing, dormancy early in the customer lifecycle severely depresses customer lifetime value (LTV). Waiting until Day 60 to detect churn is too late; by Day 14, user behavioral intent has solidified, creating an optimal window for intervention.

---

## Key Definitions & Business Rules

- **Prediction Point**: Day 14 after signup. Features strictly query behavioral events occurring between `signup_date` and `signup_date + 14 days`.
- **Dormancy Definition**: A user is dormant if they have **0 app logins (sessions) and 0 executed trades** between **Day 61 and Day 90** after signup.
- **Evaluation Split**: Chronological train/test split. Signups before `2025-10-01` form the training set; signups on or after `2025-10-01` form the hold-out test set.
- **Unit Economics**:
  $$\text{Expected Value (EV)} = (\text{Predicted Risk} \times \text{Assumed Save Rate} \times \text{Customer LTV}) - ₹15 \text{ (Contact Cost)}$$
  **Intervention Rule**: Contact *only* users with positive net expected value ($\text{EV} > 0$).

---

## Behavioral Segments & Playbook

| Segment | Day-14 Classification Rule | Save Rate | Assumed LTV | Channel | Prescribed Action |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Burned** | Traded & worst single trade P&L $\le -₹250$ | 18% | ₹2,200 | RM Call | Risk management walkthrough & stop-loss guidance |
| **Hesitant** | Account funded, but 0 trades placed | 24% | ₹1,800 | WhatsApp | 3-step first-trade video & curated starter ETF list |
| **Browser** | Unfunded, but added $\ge 6$ stocks to watchlist | 15% | ₹1,200 | In-app Push | Real-time market alert on tracked stocks with 1-click UPI funding |
| **Unfunded** | Unfunded and $< 6$ watchlist additions | 8% | ₹800 | SMS | Zero account maintenance charge (AMC) prompt with ₹100 minimum deposit |
| **Monitor** | Regular active traders or profitable accounts | 4% | ₹1,500 | Email | Weekly curated market intelligence & sector digest |

---

## Tech Stack
Built strictly with the mandated libraries:
- **Language**: Python 3.11+
- **Database**: SQLite 3 (native `sqlite3`, queries executed via SQL files)
- **Data & Modeling**: `pandas`, `numpy`, `scikit-learn`, `scipy`
- **Application & Visualization**: `Streamlit` (>=1.50), `Plotly`
- **Testing**: `pytest`

---

## Folder Layout
```text
retainai/
├── SPEC.md                     # Source of truth specification
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # Product documentation and runbook
├── .streamlit/
│   └── config.toml             # Theme tokens and server configuration
├── sql/                        # SQL queries executed exclusively via SQLite
│   ├── funnel.sql              # Onboarding conversion funnel
│   ├── retention.sql           # Monthly cohort retention matrix
│   ├── time_to_first_trade.sql # First trade speed vs. dormancy analysis
│   ├── features_day14.sql      # Day-14 behavioural feature extraction
│   └── label_dormancy.sql      # Ground-truth Day 61-90 dormancy calculation
├── src/
│   ├── config.py               # Central configuration, unit economics, segment definitions
│   ├── generate_data.py        # 20,000 user synthetic data generator (seed 42)
│   ├── build_db.py             # SQLite schema initialization, data population, and validation
│   ├── features.py             # Feature preprocessing and column encoding
│   ├── segments.py             # Rule-based segmentation and expected value engine
│   ├── stats.py                # Sample-size calculator and two-proportion hypothesis testing
│   ├── train.py                # Baseline & Gradient Boosting models, OOF scoring, permutation importance
│   └── pipeline.py             # Master orchestrator script
├── app/
│   ├── main.py                 # Streamlit entry point with grouped navigation
│   ├── ui.py                   # Design system tokens, Public Sans CSS, Indian rupee formatting
│   ├── data.py                 # Cached data access layer
│   └── views/
│       ├── overview.py         # Five-figure strip, funnel, retention heatmap, trade timing
│       ├── risk_queue.py       # Filterable ranked queue, CSV export, user diagnostic inspection
│       ├── segments_playbook.py# Portfolio EV by segment, economics table, operational playbook
│       ├── experiment_planner.py# A/B sample-size calculator, stopping rules, two-proportion test
│       └── model_threshold.py  # Model metrics, drivers, ROC curve, optimal contact threshold
├── tests/
│   ├── test_leakage.py         # Day-14 leakage assertion (pruning and injection)
│   ├── test_segments.py        # Segment assignment and expected value math tests
│   ├── test_stats.py           # Statistical calculations and hypothesis tests
│   ├── test_train.py           # Model artifacts and scoring validation
│   └── test_views.py           # Streamlit view smoke tests
└── data/                       (git-ignored)
    ├── raw/retainai.db         # SQLite database
    └── processed/
        ├── scores.csv          # 20,000 scored users with out-of-fold risk and recommendations
        └── metrics.json        # Hold-out evaluation metrics and permutation importances
```

---

## How to Run from a Clean Clone

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the End-to-End Pipeline
Generates synthetic data, creates the SQLite database, validates SQL queries, extracts Day-14 features, trains baseline and gradient boosting models, and scores all 20,000 users:
```bash
python -m src.pipeline
```

### 3. Run Test Suite
Executes all 10 unit and integration tests (including the Day-14 post-cutoff leakage test):
```bash
pytest
```

### 4. Launch the Streamlit Console
```bash
streamlit run app/main.py
```
Open `http://localhost:8501` in your browser.

---

## Design System

In compliance with `SPEC.md`:
- **Palette**: Cool grey canvas (`#F5F6F8`), white surfaces (`#FFFFFF`), ink (`#17212B`), one petrol accent (`#0E5A6B`), muted red (`#A63D40`) and amber (`#B7791F`) used exclusively for risk.
- **Typography**: Single typeface (**Public Sans**) enforced across all text, inputs, and charts.
- **Key Figures**: Displayed in continuous ruled horizontal strips (`border-top` and `border-bottom: 1px solid #E2E5E9`) rather than rows of cards.
- **Currency**: Indian digit grouping (`₹1,23,456` and compact `₹54.20L`).
- **Restraint**: Zero emoji, gradients, drop shadows, all-caps text, or decorative animations.
- **Charts**: Minimalist Plotly figures with hidden toolbars, `#ECEEF1` light gridlines, and direct data labels.

---

## Limitations & Honest Data Science Caveats

1. **Synthetic Data**: Distributions reflect simulated behavioral rules calibrated to industry averages; real brokerage environments exhibit non-linear macroeconomic shocks and market sentiment shifts.
2. **Correlation vs. Causation**: High risk denotes strong association with churn; intervention will only succeed if the underlying root causes are causally reversible.
3. **Assumed Save Rates & LTVs**: The ₹15 contact threshold and segment save rates are operational assumptions that must be empirically measured via controlled A/B experiments.
4. **Day-14 Information Horizon**: The model intentionally ignores events after Day 14 to avoid lookahead bias. Shocks occurring on Day 30 or Day 45 (e.g., sudden market crashes or customer support escalations) cannot be predicted by this model.
5. **Static Contact Costs**: Contact cost is modeled at a uniform ₹15 per user; in practice, automated notifications cost substantially less than manual Relationship Manager phone outreach.

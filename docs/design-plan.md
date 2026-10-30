# RetainAI: Terminal Design & Architecture Plan (Phase 0)

**Role:** Senior Product Manager & Senior Product Designer  
**Target:** High-density institutional retention console for retail broking (inspired by Zerodha Kite, Upstox Pro, Groww Web, and Bloomberg Terminal)  
**Deliverable:** System specification, design tokens, component architecture, ASCII wireframes, and implementation roadmap.

---

## 1. System Design Tokens & Theme Specification

The interface is engineered around an 8px modular grid. Borders define visual containment rather than cards, elevation, or drop shadows. Dark theme is the default for terminal operational density; light theme is selectable via the global top bar toggle.

### 1.1 Color Tokens Table

| Token Name | Dark Theme (Default) | Light Theme | Semantic Role |
| :--- | :--- | :--- | :--- |
| `COLOR_CANVAS` | `#0E1217` | `#F4F5F7` | Workspace background |
| `COLOR_PANEL` | `#151B23` | `#FFFFFF` | Primary surface container, tables, charts |
| `COLOR_RAISED` | `#1B232D` | `#F8F9FA` | Hover states, active tabs, header rows |
| `COLOR_BORDER` | `#263040` | `#DDE2E8` | Structural dividing rules, panel outlines |
| `COLOR_BORDER_SUBTLE` | `#1B232D` | `#ECEEF1` | Row dividers, light gridlines |
| `COLOR_TEXT_PRIMARY` | `#E6EAF0` | `#17212B` | Core data, high-emphasis values, headers |
| `COLOR_TEXT_MUTED` | `#8C98A8` | `#5A6572` | Secondary labels, descriptions, units |
| `COLOR_ACCENT_TEAL` | `#00A389` | `#0E5A6B` | Primary interactive accent, selected state, brand |
| `COLOR_POSITIVE_GREEN`| `#10B981` | `#059669` | Retained, positive EV, winning A/B test |
| `COLOR_NEGATIVE_RED`  | `#EF4444` | `#DC2626` | Churn risk, negative EV, loss-making trade |
| `COLOR_WARNING_AMBER` | `#F59E0B` | `#D97706` | Caution, moderate risk, borderline significance |
| `COLOR_MONO_ID`       | `#94A3B8` | `#475569` | Monospace user identifiers, transaction IDs |

### 1.2 Typography & Scale

- **Primary Font Family:** `'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Monospace Font Family:** `'IBM Plex Mono', 'JetBrains Mono', 'SF Mono', Consolas, monospace`
- **Numeric Formatting Rule:** `font-variant-numeric: tabular-nums` applied globally to all numbers, currency values, percentages, and table cells to prevent horizontal jiggle during filter updates.
- **Corner Radii:**
  - `RADIUS_CONTROL = 3px` (Inputs, buttons, segmented controls)
  - `RADIUS_PANEL = 4px` (Main data containers, ticket cards)

```
Scale:
- Header 1 (Page Title):     18px / 600 weight / line-height 24px
- Header 2 (Section Title):  14px / 600 weight / line-height 20px
- Body / Regular Text:       13px / 400 weight / line-height 18px
- Micro / Captions:          11px / 500 weight / line-height 14px
- Primary Data Figures:      22px / 700 weight / line-height 26px (tabular figures)
- Monospace Data IDs:        12px / 400 weight (tabular figures)
```

### 1.3 Strict Prohibitions (What We Will NOT Do)

1. **No Drop Shadows or Glows:** Structural hierarchy is achieved purely through 1px solid border tokens (`#263040` / `#DDE2E8`) and surface fills (`#151B23` / `#FFFFFF`).
2. **No All-Caps Labels:** Sentence case everywhere (e.g. "Net expected return", not "NET EXPECTED RETURN").
3. **No Decorative Animation or Gradients:** Instant data response. Transitions are restricted to subtle 100ms background hover highlights.
4. **No Emoji:** Professional terminal aesthetic. Operational status is expressed through sign, label, arrow (`+12.4% ▲`), or dot indicator.
5. **No Color-Only Signalling:** Every semantic status pairs color with text, an icon, or directional sign (+/-).

---

## 2. Shell Architecture

The screen layout comprises three structural zones:

```
+--------------------------------------------------------------------------------------------------------------------+
|  TOP BAR:  RetainAI | Cohort: 2025 Jan-Dec | Score: Day 14 | Model: v1.0.0 (GB) | As-of: 2025-12-31 | Theme: [Dark]  |
+---------------------+----------------------------------------------------------------------------------------------+
| LEFT RAIL (180px)   | MAIN CONTENT WORKSPACE (Fluid: 1280px to 1920px+)                                            |
|                     |                                                                                              |
| MONITOR             | [Page Title]                                                                                 |
| > Overview          | [One-line plain-language directive]                                                          |
|   Risk queue (18k)  |----------------------------------------------------------------------------------------------|
|                     | [Fixed-Height KPI Strip / Ticker Cells]                                                      |
| PLAN                |----------------------------------------------------------------------------------------------|
|   Segments (5)      | [Page-Specific Workstation Grid: Tables, Master-Detail, Analytics]                           |
|   Experiments       |                                                                                              |
|                     |                                                                                              |
| EVALUATE            |                                                                                              |
|   Model & Threshold |                                                                                              |
|                     |                                                                                              |
+---------------------+----------------------------------------------------------------------------------------------+
| STATUS LINE: Filter: All | Showing: 18,168 rows | Approved: 142 | Cache: 18ms | Session: Active                        |
+--------------------------------------------------------------------------------------------------------------------+
```

### 2.1 Top Bar (Global System Header)
- Compact 40px height fixed strip.
- **Product Brand:** `RetainAI` in 14px bold with small version pill (`v1.0`).
- **Telemetry Ticker:** Cohort timeline (`2025 Signups`), Evaluation Day (`Day 14`), Hold-out ROC AUC (`0.693`), Snapshot timestamp (`2025-12-31`).
- **Theme Switcher:** Compact toggle button (`Dark` / `Light`) updating Streamlit session state and injecting theme variables instantly.

### 2.2 Left Rail (Terminal Navigation)
- Width: 180px fixed width, eliminating wide wasted sidebar space.
- Grouped into three distinct functional categories:
  - `MONITOR` (Overview, Risk queue)
  - `PLAN` (Segments and playbook, Experiment planner)
  - `EVALUATE` (Model and threshold)
- Interactive buttons with 3px left-border accent bar on active selection (`COLOR_ACCENT_TEAL`), dark hover fill, and inline count badges. No browser radio circles.

### 2.3 Bottom Status Line (Operational Context)
- Height: 24px anchored status bar at the bottom of the workspace.
- Reports active filter summary, displayed row counts, pending triage items, cache latency, and pipeline data freshness.

---

## 3. Authoritative Economics Engine (`src/economics.py`)

To eliminate the discrepancy where Expected Value diverged across pages (₹10.15L vs ₹10,15,143 vs ₹17.04L), all financial calculations will be consolidated into a single authoritative module:

```python
# src/economics.py
"""Single source of truth for RetainAI unit economics and expected value."""

CONTACT_COST_INR = 15.0

SEGMENT_ECONOMICS = {
    "Hesitant": {"save_rate": 0.24, "ltv": 2500.0, "channel": "In-app walk-through"},
    "Burned":   {"save_rate": 0.18, "ltv": 1800.0, "channel": "Relationship call"},
    "Browser":  {"save_rate": 0.15, "ltv": 1200.0, "channel": "WhatsApp nudge"},
    "Unfunded": {"save_rate": 0.08, "ltv": 800.0,  "channel": "SMS push"},
    "Monitor":  {"save_rate": 0.04, "ltv": 1500.0, "channel": "Email digest"},
}

def calculate_expected_value(risk: float, segment: str, contact_cost: float = CONTACT_COST_INR) -> float:
    econ = SEGMENT_ECONOMICS.get(segment, {"save_rate": 0.10, "ltv": 1000.0})
    return (risk * econ["save_rate"] * econ["ltv"]) - contact_cost

def break_even_risk(segment: str, contact_cost: float = CONTACT_COST_INR) -> float:
    econ = SEGMENT_ECONOMICS[segment]
    return contact_cost / (econ["save_rate"] * econ["ltv"])
```

**Unit Test Contract (`tests/test_economics.py`):**
A unit test will assert that summing `expected_value` across `scores.csv` produces the exact same number whether aggregated at the cohort, segment, or filter level.

---

## 4. Page Layouts & ASCII Wireframes

### Page 1: Overview (Command Centre)
```
+--------------------------------------------------------------------------------------------------------------------+
| OVERVIEW                                                                                                           |
| Monitor full-funnel activation milestones, monthly retention decay, and transaction velocity.                     |
+--------------------------------------------------------------------------------------------------------------------+
| [ SIGNUPS (2025) ] | [ KYC COMPLETED ]   | [ FUNDED ACCOUNTS ] | [ TRADED <= 30D ]   | [ DORMANT (DAY 90) ]        |
| 20,000             | 83.7% (16,745)      | 57.4% (9,615)       | 63.9% (6,145)       | 37.1% (7,420)               |
| Target: 100%       | +1.2% vs 3m avg ▲   | -0.8% vs 3m avg ▼   | +2.4% vs 3m avg ▲   | -1.1% vs 3m avg ▲ (good)    |
| [~~sparkline~~]    | [~~sparkline~~]     | [~~sparkline~~]     | [~~sparkline~~]     | [~~sparkline~~]             |
+--------------------------------------------------------------------------------------------------------------------+
| ONBOARDING FUNNEL (HYBRID TABLE-CHART)                  | DORMANCY BY TRADING VELOCITY                             |
| Stage             Count   % Cohort  Step Conv  Leakage  | Time to 1st Trade     Users   Dormancy Rate  Risk Delta  |
| 1. Signups       20,000   100.0%    --         --       | 0 - 3 days            2,840   14.2%  [===]   -22.9%  (Low)|
| 2. KYC Verified  16,745    83.7%    83.7%      -3,255   | 4 - 7 days            1,950   17.8%  [====]  -19.3%       |
| 3. Account Funded 9,615    48.1%    57.4% [!]  -7,130   | 8 - 14 days           1,355   26.4%  [======] -10.7%      |
| 4. 1st Trade 30d  6,145    30.7%    63.9%      -3,470   | 15 - 30 days            820   34.1%  [========] -3.0%     |
| [!] Primary Bottleneck: KYC-to-Funding (42.6% drop)     | Unfunded / No Trade   13,035  46.9%  [===========] +9.8%  |
|                                                         | Action: [Open Hesitant Queue (3,470 users) ->]            |
+---------------------------------------------------------+----------------------------------------------------------+
| MONTHLY COHORT RETENTION HEATMAP (% Active at Interval)                                                            |
| Cohort        Size      Day 0-14           Day 15-30          Day 31-60          Day 61-90 (Dormancy Gate)     |
| 2025-01      1,640      100.0%             82.1%              71.4%              63.2% (Dormancy 36.8%)        |
| 2025-02      1,580      100.0%             81.8%              70.9%              62.7% (Dormancy 37.3%)        |
| ...          ...        ...                ...                ...                ...                           |
| 2025-12      1,720      100.0%             84.2%              73.1%              64.5% (Dormancy 35.5%)        |
+--------------------------------------------------------------------------------------------------------------------+
```

### Page 2: Risk Queue (Master & Detail)
```
+--------------------------------------------------------------------------------------------------------------------+
| RISK QUEUE                                                                                                         |
| Prioritized triage queue of accounts approaching day-14 checkpoint. Rank ordered by positive net expected value.   |
+--------------------------------------------------------------------------------------------------------------------+
| SEGMENT TABS: [ All (18,168) ] [ Hesitant (6,320) ] [ Burned (1,240) ] [ Browser (2,180) ] [ Unfunded (8,428) ]    |
| TOOLBAR: Channel: [ All v ] | Min Risk: [ 25% |==o====== 100% ] | Search User: [ USR-____ ] | [Export Approved CSV]|
+-------------------------------------------------------------------+------------------------------------------------+
| MASTER TABLE (65% Width, Row-Selection Enabled)                   | DETAIL: INTERVENTION TICKET (35% Sticky Drawer)|
| User ID   Segment   Channel   Risk %    Net EV    Days   Action   | USER TICKET: USR-09412                         |
| USR-09412 Hesitant  Referral  42.1%  [=] ₹142.80   12d   Select > | Segment: Hesitant | Channel: Referral          |
| USR-18231 Hesitant  Organic   38.4%  [=] ₹128.50   14d   Select   | Signup: 2025-10-14 (12d ago) | KYC: Verified   |
| USR-04128 Burned    Direct    54.2%  [=] ₹160.40   11d   Select   |------------------------------------------------|
| USR-11902 Hesitant  Google    36.2%  [=] ₹120.20   13d   Select   | DORMANCY RISK GAUGE: 42.1% (High)              |
| USR-00481 Browser   Affiliate 61.0%  [=]  ₹94.80   14d   Select   | Expected Return: ₹142.80 (Net of ₹15 cost)     |
| USR-08214 Burned    Referral  48.0%  [=] ₹140.60   10d   Select   |------------------------------------------------|
| ... (28px row height, tabular monospace IDs, sticky header)      | DRIVERS (DAYS 0-14):                           |
|                                                                   | ▲ Raising Risk:                                |
|                                                                   |   - Zero trades placed despite funded account  |
|                                                                   |   - Session frequency dropped 65% in week 2    |
|                                                                   | ▼ Protective Signals:                          |
|                                                                   |   - Completed KYC within 24h of signup         |
|                                                                   |   - Added 8 stocks to active watchlist         |
|                                                                   |------------------------------------------------|
|                                                                   | PLAYBOOK INTERVENTION:                         |
|                                                                   | Action: In-app guided walkthrough              |
|                                                                   | Channel: In-app prompt + Push notification     |
|                                                                   | Copy Preview (Editable):                       |
|                                                                   | +--------------------------------------------+ |
|                                                                   | | "Your account is funded and ready. Here is | |
|                                                                   | | a 60-second video on placing your 1st order"||
|                                                                   | +--------------------------------------------+ |
|                                                                   | [ APPROVE (Enter) ]  [ SKIP (S) ]  [ SNOOZE ]  |
|                                                                   | Triage Progress: 142 Approved | 18 Skipped     |
+-------------------------------------------------------------------+------------------------------------------------+
```

### Page 3: Segments & Playbook
```
+--------------------------------------------------------------------------------------------------------------------+
| SEGMENTS AND PLAYBOOK                                                                                              |
| Deterministic behavioral classification rules, unit economics, and standard operating procedures.                  |
+--------------------------------------------------------------------------------------------------------------------+
| [ TOTAL COHORT ]    | [ CONTACTABLE USERS ] | [ TOTAL NET EV ]      | [ AVG EV / USER ]   | [ BLENDED SAVE RATE ]  |
| 20,000              | 18,168 (90.8%)        | ₹10.15L               | ₹55.88              | 14.8%                  |
| 5 Segments          | Net EV > ₹0           | After ₹15 Contact Fee | Per Outreach        | Weighted Average       |
+--------------------------------------------------------------------------------------------------------------------+
| SEGMENT ECONOMICS LEDGER (COMPACT MATRIX TABLE)                                                                    |
| Segment   Trigger Rule (Plain English)       Users  Share%  Avg Risk  Save Rate  LTV (₹)  Net EV (₹)  Break-Even R*|
| Hesitant  Funded account, 0 trades in 14d    6,320   31.6%     37.8%      24.0%   ₹2,500     ₹4.82L          2.5%  |
| Burned    Traded, worst trade loss <= -₹250  1,240    6.2%     58.4%      18.0%   ₹1,800     ₹1.68L          4.6%  |
| Browser   Unfunded, 6+ watchlist adds in 14d 2,180   10.9%     49.2%      15.0%   ₹1,200     ₹1.24L          8.3%  |
| Unfunded  Unfunded, < 6 watchlist adds       8,428   42.1%     41.5%       8.0%     ₹800     ₹1.86L         23.4%  |
| Monitor   Active trader / profitable trade   1,832    9.2%     12.1%       4.0%   ₹1,500     ₹0.55L         25.0%  |
+--------------------------------------------------------------------------------------------------------------------+
| PLAYBOOK TABS: [ Hesitant ]  [ Burned ]  [ Browser ]  [ Unfunded ]  [ Monitor ]                                    |
| +----------------------------------------------------------------------------------------------------------------+ |
| | HESITANT PLAYBOOK SPECIFICATION                                                                                | |
| | Objective: Overcome first-order execution anxiety for verified, funded investors.                              | |
| | Trigger Criteria: `account_funded == 1` and `trade_count_d14 == 0`                                              | |
| | Delivery Channel: In-App Walkthrough & WhatsApp Prompt | Target Delivery SLA: Day 14, 10:00 AM                  | |
| | Assumed Economics: 24.0% Save Rate | ₹2,500 Investor LTV | Net EV Contribution: ₹4.82 Lakh                     | |
| |                                                                                                                | |
| | Standard Messaging Copy Template:                                                              [ Copy to Clipboard ]| |
| | "Your account is funded and ready. Here is a 60-second video on placing your first delivery trade with zero    | |
| | brokerage on equity delivery."                                                                                 | |
| +----------------------------------------------------------------------------------------------------------------+ |
```

### Page 4: Experiment Planner
```
+--------------------------------------------------------------------------------------------------------------------+
| EXPERIMENT PLANNER                                                                                                 |
| Statistical sample sizing, minimum detectable effect modeling, and two-proportion experiment read-out.              |
+--------------------------------------------------------------------------------------------------------------------+
| 1. TRIAL CONFIGURATION & SAMPLE SIZING                                                                             |
| Segment Preset: [ Hesitant (24% Baseline) v ] | Alpha: [ 0.05 (95% CI) ] | Power: [ 0.80 v ]                       |
|                                                                                                                    |
| Baseline Save Rate (p1): [ 24.0% |======o======= 40% ]  (24.0%) | Target Relative Lift (MDE): [ 15% |=o======= 50% ]|
| Daily Eligible Traffic:  [ 120 users/day ]                       | Required Duration:          [ 24 Days ]          |
+--------------------------------------------------------------------------------------------------------------------+
| [ PER-ARM SAMPLE ]  | [ TOTAL SAMPLE ]      | [ TARGET SAVE RATE ]  | [ MINIMUM DURATION ] | [ PROJECTED NET GAIN ]|
| 1,420 users         | 2,840 users           | 27.6% (+3.6% Abs)     | 24 Calendar Days     | ₹88,750 (Net)         |
+--------------------------------------------------------------------------------------------------------------------+
| POWER CURVE: Sample Size Required vs Relative MDE       | STATISTICAL STOPPING & DECISION PROTOCOL                 |
| Sample Size                                             | [ SHIP TO 100% (ROLLOUT) ]                               |
| 5000 |                                                  | - P-value < 0.05 and lower bound of 95% CI > 0.          |
| 4000 |   \                                              | - Observed Lift >= 15.0% relative MDE.                   |
| 3000 |     \                                            | - Net EV gain exceeds intervention outreach budget.      |
| 2000 |       *- (Current: 1,420 @ 15% MDE)              | [ ITERATE VARIANT ]                                      |
| 1000 |           \___                                   | - 0.05 <= P-value < 0.20 with directionally positive lift|
|    0 +---------------------------------                 | [ STOP & ARCHIVE ]                                       |
|      5%    10%   15%   20%   25%   30%   MDE            | - P-value >= 0.20 or negative observed lift.             |
|                                                         | [ Download Pre-Registration Brief (.md) ]                |
+---------------------------------------------------------+----------------------------------------------------------+
| 2. LIVE EXPERIMENT RESULT READ-OUT                                                                                 |
| Control: [ 340 saved ] / [ 1,420 total ] (23.94%)       | Variant: [ 402 saved ] / [ 1,420 total ] (28.31%)        |
| Absolute Lift: +4.37% | Relative Lift: +18.25%          | Z-Score: 2.714 | P-Value: 0.0066                         |
| 95% Confidence Interval: [+1.22%, +7.52%]               | VERDICT: [ STATISTICALLY SIGNIFICANT WIN - SHIP TO 100% ]|
+--------------------------------------------------------------------------------------------------------------------+
```

### Page 5: Model & Threshold
```
+--------------------------------------------------------------------------------------------------------------------+
| MODEL & THRESHOLD GOVERNANCE                                                                                       |
| Chronological hold-out evaluation, aggregate driver importance, and capacity-constrained threshold optimization.   |
+--------------------------------------------------------------------------------------------------------------------+
| [ HOLD-OUT ROC AUC ] | [ HOLD-OUT PR AUC ]   | [ BRIER SCORE ]       | [ TOP-DECILE LIFT ]  | [ TOP-DECILE CAPTURE ] |
| 0.693                | 0.512                 | 0.187                 | 1.75x                | 28.4%                  |
| Baseline: 0.641 (+8%)| Baseline: 0.448 (+14%)| Perfect: 0.000        | Random: 1.00x        | Top 10% captures 28%   |
+--------------------------------------------------------------------------------------------------------------------+
| MODEL SCORECARD (HOLDOUT: SIGNUPS >= 2025-10-01)        | ROC CURVE & DECISION CALIBRATION                         |
| Metric              Logistic Reg.   HistGradientBoost   | Sensitivity (TPR)                                        |
| ROC AUC             0.641           0.693  [+0.052 ▲]   | 1.0 |                .---' (GB AUC: 0.693)                 |
| PR AUC              0.448           0.512  [+0.064 ▲]   | 0.8 |             .-'                                    |
| Brier Score         0.198           0.187  [-0.011 ▲]   | 0.6 |          .-'                                       |
| Top-Decile Lift     1.42x           1.75x  [+0.33x ▲]   | 0.4 |       .-'  / (Random: 0.50)                        |
| Top-Decile Capture  21.2%           28.4%  [+7.2%  ▲]   | 0.2 |   .--'    /                                        |
| Best Model: HistGradientBoosting (Selected for Scoring) | 0.0 +----------------------------------                  |
|                                                         |     0.0   0.2   0.4   0.6   0.8   1.0   FPR             |
+---------------------------------------------------------+----------------------------------------------------------+
| AGGREGATE PERMUTATION IMPORTANCE (Grouped Features)     | CAPACITY-CONSTRAINED THRESHOLD OPTIMIZER                 |
| Feature Family                 Importance Score         | Parameters: Contact Cost: [ ₹15 ] | Save Rate Mult: [1.0x]|
| Days Since Last Session        [===================] 38%| Weekly Calling Capacity: [ 2,500 contacts / week ]       |
| Total Trades in First 14 Days  [==============     ] 27%|                                                          |
| Account Funding Amount (₹)     [===========        ] 21%| Optimization Read-Out:                                   |
| Acquisition Channel (Aggregated)[=======            ] 14%| - Economic Break-Even Threshold: 18.2% risk              |
| Watchlist Adds                 [====               ]  8%| - Operational Capacity Threshold: 34.5% risk             |
| Support Tickets (Tech/KYC)     [==                 ]  4%| - Recommended Cutoff: 34.5% (Capacity Constrained)       |
| (One-hot channels rolled up into root channel factor)   | - Contacts Selected: 2,500 / week                        |
|                                                         | - Marginal EV of 2,500th Contact: +₹24.80 (Positive ROI) |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 5. Component Inventory & Implementation Specifications

All components will reside in `app/ui/` or `app/ui.py` to ensure modularity:

1. **`Shell` & `TopBar`**: Renders top metadata banner, active telemetry, and theme toggling logic.
2. **`LeftRail`**: Grouped navigation sidebar with SVG icons, indicator accent bar, and counts.
3. **`KpiCell`**: Uniform fixed-height KPI card with tabular numbers, subtitle, delta badge, and optional sparkline.
4. **`DataTable`**: Streamlit `st.dataframe` styled with row selection (`selection_mode="single_row"`), formatted monospace IDs, badge tags, and sticky headers.
5. **`InterventionTicket`**: Right-side order ticket view rendering user risk score gauge, separate risk/protective drivers, copy preview, and action buttons.
6. **`SegmentTabs`**: Horizontal tab bar with count pills for instantaneous single-click segment switching.
7. **`ChartTheme`**: Plotly figure styling helper enforcing dark/light background tokens, zero margin waste, fixed right gutter for direct bar labels, and horizontal orientations for categorical metrics.
8. **`EconomicsModule`**: `src/economics.py` providing single-truth calculations for all 5 views.

---

## 6. Execution Roadmap

- **Phase 0 (Current):** UX Audit (`docs/ux-audit.md`) & Design Plan (`docs/design-plan.md`) submitted for stakeholder review. **Code frozen until approval.**
- **Phase 1:** Design System & Shell (tokens, dark/light switcher, top bar, left rail, status line, base component helpers).
- **Phase 2:** Command Centre (Overview) & Master-Detail Risk Queue with Order Ticket.
- **Phase 3:** Segments & Playbook, Experiment Planner, and Model & Capacity Threshold Governance.
- **Phase 4:** End-to-end verification across 1920x1080, 1440x900, and 1280x720 in both themes; pytest suite confirmation; before/after documentation.

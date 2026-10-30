# RetainAI: Comprehensive UX & Product Audit (Phase 0)

**Authors:** Senior Product Manager (Brokerage Internal Tools) & Senior Product Designer (Trading & Terminal Systems)  
**Target Audience:** Engineering, Product Leadership, and Brokerage Operations  
**Baseline Workspace:** Streamlit 1.66, Plotly, SQLite3, Scikit-Learn  
**Reference Screenshots:** `docs/before/*.png` (1440x900 and 1920x1080 viewports)

---

## 1. Executive Summary & Terminal Philosophy

RetainAI was initially structured as a traditional exploratory web dashboard. For a retention operations team at a retail brokerage (handling 20,000 to 500,000 monthly signups across discount and full-service models like Zerodha, Upstox, or Groww), a generic dashboard fails operational workflows.

A retention console is an **action terminal**, not a reporting portal. Analysts and PMs spend 4–6 hours daily in this interface:
1. They monitor cohort health and drop-off leaks.
2. They execute daily triage queues, approving or suppressing intervention batches (calls, WhatsApp nudges, push notifications).
3. They balance intervention economics: calling or SMS costs money (₹15/touch), so every touchpoint must yield positive marginal expected return ($\text{EV} > 0$).
4. They run statistical experiments and govern ML models.

### Primary Deficiencies in Baseline App
- **Information Density is Low:** Excessive whitespace, massive margins, large card footprints, and consumer-dashboard styling that forces unnecessary scrolling.
- **Disconnected Master-Detail:** Reviewing an individual user requires scrolling past a 100-row table and picking an ID from an isolated dropdown.
- **Economic Inconsistencies:** Expected Value calculations diverge between pages (₹10.15L vs ₹17.04L).
- **Misleading Signal Polarity:** Protective actions (e.g. trading frequently) are displayed as risk drivers.
- **Formatting & Layout Breakages:** White text clipping outside bars, rotated categorical axis labels, truncated table headers, and misaligned KPI blocks.

---

## 2. Exhaustive Audit: Ranked by Severity

### Priority 1: Critical Product Logic & Operational Integrity (Blockers)

| ID | Issue Description | Root Cause in Code | Operational Impact | Required Fix |
| :--- | :--- | :--- | :--- | :--- |
| **P1-1** | **Total Expected Value differs across pages** (₹10.15L vs ₹10,15,143 vs ₹17.04L) | `model_threshold.py` calculates portfolio value using a flat global formula across all users, whereas `risk_queue.py` and `segments_playbook.py` apply segment-specific save rates and LTVs. | Destroys credibility with Finance and CRM leadership. Executives cannot reconcile projected retention gains across screens. | Build a single centralized economics module (`src/economics.py` / `app/economics.py`) that exports authoritative formulas for save rates, LTV, contact cost, and net EV. Enforce equality with a dedicated unit test. |
| **P1-2** | **Protective signals listed as risk drivers** | `src/features.py` and `risk_queue.py` select top feature importances by absolute magnitude without filtering by sign of the partial dependence or log-odds direction. | An analyst reviewing an investor who placed 6 profitable trades sees "Trades in 14d: 6" listed as a "Risk Driver". Operations calls the user with contradictory messaging. | Deconstruct drivers into two distinct categories: **Dormancy Risk Factors** (features pushing probability towards churn) and **Protective Factors** (features pulling probability towards retention). |
| **P1-3** | **Threshold optimizer recommends contacting 100% of users** | In `model_threshold.py`, the net value optimization curve uses an unconstrained search that peaks at a 5.0% risk cutoff, capturing ~99% of signups. | Operational absurdity. A calling desk cannot call 19,800 users with a 10-person team. No operational capacity constraint is modeled. | Redesign threshold optimizer to incorporate: (1) Segment break-even risk $R^* = \frac{\text{Cost}}{\text{SaveRate} \times \text{LTV}}$, (2) Weekly CRM capacity constraint slider, and (3) Marginal EV of the last contacted investor. |
| **P1-4** | **Top of the Risk Queue is completely monopolized by one segment** | In `risk_queue.py`, default sorting is strictly descending by `expected_value`. Because the "Hesitant" segment has the highest LTV (₹2,500), all top 100 rows belong to Hesitant users. | The PM cannot action high-risk "Burned" or "Browser" cohorts without applying manual multi-click dropdown filters. | Introduce persistent Segment Filter Tabs with badge counters ("All: 18,168", "Hesitant: 6,320", "Burned: 1,240", "Browser: 2,180", "Unfunded: 8,428") right above the table. |
| **P1-5** | **The `Contact` column displays "Yes" on every visible row** | In `risk_queue.py`, the default filter displays users sorted by positive EV descending. All visible users meet `should_contact == True`. | Consumes 80px of horizontal data-table space with redundant identical text on every line. | Remove the redundant boolean "Contact" column. Reallocate width to actionable metrics: Risk %, Net EV (₹), Segment badge, and Days Since Signup. |

---

### Priority 2: Terminal Usability & Interaction Flaws (Major)

| ID | Issue Description | Root Cause in Code | Usability Impact | Required Fix |
| :--- | :--- | :--- | :--- | :--- |
| **P2-1** | **Detail view separated from the master table** | In `risk_queue.py`, the user inspection card is placed underneath the 100-row dataframe, driven by an unlinked selectbox. | High interaction friction. Analysts must scroll up and down repeatedly to inspect accounts, breaking flow. | Implement a terminal-grade master-detail layout: 65% width interactive table with instant row-selection (`st.dataframe` `selection_mode="single_row"`), paired with a 35% sticky "Intervention Ticket" right-hand drawer. |
| **P2-2** | **Radio-button sidebar navigation** | `app/main.py` uses `st.sidebar.radio` with default browser radio bullets. | Feels like a consumer survey form or Google Form rather than an institutional trading workstation (e.g. Kite/Bloomberg). | Build a sleek terminal left rail with grouped categories (`MONITOR`, `PLAN`, `EVALUATE`), border-left active state indicators, hover highlights, and compact typography. |
| **P2-3** | **One-hot channel columns shown as separate feature bars** | `train.py` / `model_threshold.py` computes permutation importance on dummy-encoded variables (`acquisition_channel_Direct`, `acquisition_channel_Influencer`, etc.). | Dilutes channel signal into 5 tiny bars instead of showing the holistic impact of Acquisition Channel. | Sum or pool permutation importance across one-hot feature families back to the root variable (`Acquisition Channel`). |
| **P2-4** | **Model comparison table cut off horizontally** | `model_threshold.py` nests a 3-column table inside a 50/50 split column layout next to the ROC curve. | Columns are truncated, forcing horizontal scrollbars and cutting off metric definitions. | Display the model comparison as a dedicated full-width terminal scorecard with clear delta columns (+X.XX% vs Baseline). |
| **P2-5** | **Intervention template label and quote rendered in separate boxes** | In `segments_playbook.py` and `risk_queue.py`, container cards render headers, and then invoke `render_callout()` in a detached block below. | Visual disjointedness; breaks visual containment and wastes vertical real estate. | Merge message templates, trigger rules, and copy text directly inside the playbook container. Add a single-click "Copy Copy" button. |

---

### Priority 3: Visual Polish, Typography & Information Density (Moderate)

| ID | Issue Description | Root Cause in Code | Visual Impact | Required Fix |
| :--- | :--- | :--- | :--- | :--- |
| **P3-1** | **Funnel and bar labels clipped or white-on-light** | `overview.py` specifies `textposition="auto"` and `color="#FFFFFF"` on horizontal bar charts. | White labels render over light grey backgrounds outside short bars, becoming completely illegible. | Position data labels outside bars in a reserved right gutter with strict contrast tokens (`#E6EAF0` in dark, `#17212B` in light). |
| **P3-2** | **Rotated and cut-off categorical axis labels** | `overview.py` (trade timing) and `segments_playbook.py` (distribution) use vertical bars with wide text categories. | Labels tilt at 45°, collide with axis boundaries, or truncate ellipses (`Never Tr...`). | Convert all categorical charts to horizontal bar layouts with left-aligned category labels. |
| **P3-3** | **KPI labels wrapping, causing metric value misalignment** | In `render_metric_strip`, label strings have uneven lengths ("Average EV per contacted user" vs "Total cohort"). | Label containers wrap unevenly to 2 lines, pushing values out of horizontal alignment. | Implement a rigid tabular KPI strip with fixed header line-clamp, tabular figures (`tabular-nums`), and structured metadata subtext. |
| **P3-4** | **Input sliders lack unit suffixes and synchronized number inputs** | `risk_queue.py` and `experiment_planner.py` use generic sliders (`0.05`, `15`, `120`) with no unit tags. | Cognitive load: user must guess whether a slider represents rupees, percentages, or raw user counts. | Add explicit unit suffixes (`format="%d%%"`, `format="₹%d"`), visible min/max bounding pills, and adjacent numeric input boxes. |
| **P3-5** | **Excessive 4-decimal precision on business metrics** | `model_threshold.py` prints metrics as `0.6934`, `0.5123`, `0.1872`. | Creates false precision and clutter. Trading desks demand clean, scannable numbers. | Restrict all probability/ML metrics to 3 decimals (`0.693`), conversion rates to 1 decimal (`83.7%`), and currency to whole rupees. |
| **P3-6** | **Truncated table columns in dataframes** | `st.dataframe` renders columns with equal default widths, clipping user IDs, channel names, and financial figures. | Ellipses obscure data; columns must be manually resized by the user. | Use `st.column_config` to define explicit column widths, format masks, and text wrap options. |

---

## 3. Detailed Page-by-Page Audit Findings

### Page 1: Overview (Command Centre)
- **Top Metric Strip:** Lacks temporal context. Shows total 2025 cohort figures, but provides no trend context (e.g., delta vs trailing 3 months) or cohort sparklines.
- **Conversion Funnel:** Pure bar chart fails to communicate step-level leakage clearly. A PM needs to see step-conversion percentages side-by-side with raw dropped investor counts.
- **Monthly Cohort Heatmap:** Color scale lacks standard discrete step thresholds, making slight 1% variations appear visually dramatic or washed out.
- **Trading Velocity Insight:** Highlights that trading within 7 days prevents churn, but gives no direct action. A PM reading this must manually navigate to the Risk Queue to find those users.

### Page 2: Risk Queue (Master & Detail)
- **Filters:** Bulky selectboxes occupy an entire row before the data appears.
- **Data Table:** Flat table lacks visual risk tiers. Risk percentages are numbers with no proportional visual weight (e.g. micro-bars).
- **Workflow Absence:** The analyst cannot take operational action. There are no "Approve", "Skip", or "Snooze" action triggers, and session state does not track daily triage progress.
- **Export Utility:** Exports the raw queue, but cannot filter down to only "Approved" triage items.

### Page 3: Segments & Playbook
- **Visual Balance:** Half the viewport is spent on a generic segment distribution bar chart that duplicates the economics table right below it.
- **Economics Table:** Long headers truncate. Assumed unit economics are scattered across cards rather than consolidated into a clear institutional ledger.
- **Playbook Cards:** Stacked vertically in an endless scroll. A PM reviewing the "Unfunded" playbook must scroll past 3 screen heights.

### Page 4: Experiment Planner
- **Interactive Sizing:** Sliders lack direct linkage to input numbers. Changing inputs forces page recalculation without displaying the empirical sample-size vs detectable lift power curve.
- **Decision Rules:** Displayed as static text boxes. Thresholds are generic and do not dynamically reflect the statistical parameters configured above.
- **Result Read-out:** Lacks an authoritative verdict tag (`STATISTICALLY SIGNIFICANT WIN`, `INCONCLUSIVE - ITERATE`, `UNDERPOWERED`).
- **Exporting Briefs:** No mechanism to generate a shareable experiment pre-registration document for growth engineering teams.

### Page 5: Model & Threshold
- **Model Comparison:** Displays two separate models but does not compute or highlight the relative performance delta ($\Delta$ Lift, $\Delta$ AUC).
- **Diagnostics Missing:** No calibration plot (decile predicted vs observed rate) and no cumulative gain curve to show CRM capture efficiency.
- **Feature Importance:** Raw scikit-learn feature names (`sessions_count_day14`, `worst_trade_pnl_day14`) instead of clear financial and operational titles.
- **Threshold Strategy:** Recommends contacting users down to 5% risk without accounting for contact team capacity, generating a negative ROI tail.

---

## 4. Verification Checkpoint

The issues above have been mapped directly to corresponding solutions in `docs/design-plan.md`. No application code will be modified until formal stakeholder sign-off on the architectural plan.

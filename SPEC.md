# RetainAI spec

## Product
A retention console for a retail broking app. It predicts which new investors will go dormant, explains why, and recommends one intervention per user. Dormant = no login and no trade between day 61 and day 90 after signup. Prediction point = day 14, using only the first 14 days of behaviour.

## Stack
Python 3.11, pandas, numpy, scikit-learn, scipy, SQLite (sqlite3), Streamlit 1.50+, Plotly, pytest. Nothing else.

## Folder layout
src/ (config, generate_data, build_db, features, segments, stats, train, pipeline), sql/, app/ (main.py, ui.py, data.py, views/), tests/, data/ (git-ignored), README.md, requirements.txt, .streamlit/config.toml.

## Synthetic data
20,000 users, signups spread over 2025. Fixed seed. Five tables: users(user_id, signup_date, city_tier, age_band, acquisition_channel, kyc_completed_date), funding(user_id, fund_date, amount), trades(user_id, trade_date, product, value, realized_pnl), sessions(user_id, session_date, screens_viewed, watchlist_adds), support_tickets(user_id, ticket_date, category).
Targets: about 83% complete KYC; about 57% of those add funds; about 63% of funded users place a first trade within 30 days; about 37% dormant by day 90.
Behaviour rules: channel changes intent (referral best, influencer worst); an early realised loss raises dormancy; unfunded users are more likely to go dormant; 3-4% missing values in age_band and city_tier. All assumptions live in src/config.py or at the top of generate_data.py with comments.

## SQL (files in sql/, run through SQLite, not pandas)
funnel.sql, retention.sql (monthly cohorts), time_to_first_trade.sql, features_day14.sql, label_dormancy.sql. Create a view called activity (sessions plus trades). Features must only read the first 14 days.

## Model
Logistic regression baseline and gradient boosting. Time-based split: signups before 2025-10-01 train, later signups test. Report ROC AUC, PR AUC, Brier score, top-decile capture and lift. Permutation importance with plain-language names. 5-fold out-of-fold risk for every user. Save data/processed/scores.csv and metrics.json.

## Segments (rules, not a model)
Burned: traded and worst trade P&L <= -250. Hesitant: funded, no trade. Browser: unfunded and 6+ watchlist adds. Unfunded: not funded. Monitor: everything else. One action, channel, message, assumed save rate and lifetime value per segment, declared in config. Expected value = risk x save rate x lifetime value, minus a contact cost of 15 rupees. Contact only users with positive net value.

## App pages
1. Overview: five-figure metric strip, funnel, cohort retention heatmap, dormancy by time to first trade.
2. Risk queue: filters (segment, channel, minimum risk), ranked table, CSV export, per-user reasons and message.
3. Segments and playbook: expected value by segment, summary table, playbook per segment.
4. Experiment planner: sample-size calculator, decision rule, result read-out (two-proportion test).
5. Model and threshold: metrics, drivers, ROC curve, model comparison, sliders for contact cost and save rate that show the best contact threshold.

## Design
Cool grey canvas #F5F6F8, white surfaces, ink #17212B, one petrol accent #0E5A6B, muted red #A63D40 and amber #B7791F only for risk. One typeface: Public Sans. Sentence case everywhere. Key figures in one ruled strip, not a row of identical cards. No emoji, gradients, drop shadows, all-caps labels, or decorative animation. Charts: no toolbar, light gridlines, direct data labels. Rupees use Indian digit grouping. Empty states say what to do next. Plain verbs, no marketing language.

## Quality bar
Typed functions, no dead code, no debug prints, no hard-coded paths. `python -m src.pipeline` then `streamlit run app/main.py` must work from a clean clone. pytest must pass, including a test proving features ignore anything after day 14. README states limits honestly (synthetic data, assumed save rates, correlation not causation).

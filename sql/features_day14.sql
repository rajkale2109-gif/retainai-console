-- Feature extraction at prediction point (Day 14)
-- Strictly reads ONLY behaviour and events occurring within the first 14 days of signup.
-- Any activity after date(signup_date, '+14 days') is strictly excluded.

WITH funding_d14 AS (
    SELECT
        f.user_id,
        COUNT(*) AS funding_count_d14,
        SUM(f.amount) AS total_funded_amount_d14,
        MIN(CAST(julianday(f.fund_date) - julianday(u.signup_date) AS INTEGER)) AS days_to_first_funding
    FROM funding f
    JOIN users u ON f.user_id = u.user_id
    WHERE f.fund_date <= date(u.signup_date, '+14 days')
    GROUP BY f.user_id
),
sessions_d14 AS (
    SELECT
        s.user_id,
        COUNT(*) AS session_count_d14,
        COUNT(DISTINCT s.session_date) AS active_days_d14,
        SUM(s.screens_viewed) AS total_screens_viewed_d14,
        ROUND(AVG(s.screens_viewed), 2) AS avg_screens_per_session_d14,
        SUM(s.watchlist_adds) AS total_watchlist_adds_d14,
        MAX(s.watchlist_adds) AS max_watchlist_adds_session_d14,
        MAX(CAST(julianday(s.session_date) - julianday(u.signup_date) AS INTEGER)) AS last_session_day_d14
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
    WHERE s.session_date <= date(u.signup_date, '+14 days')
    GROUP BY s.user_id
),
trades_d14 AS (
    SELECT
        t.user_id,
        COUNT(*) AS trade_count_d14,
        SUM(t.value) AS total_trade_value_d14,
        ROUND(SUM(t.realized_pnl), 2) AS total_realized_pnl_d14,
        ROUND(MIN(t.realized_pnl), 2) AS worst_trade_pnl_d14,
        SUM(CASE WHEN t.realized_pnl < 0 THEN 1 ELSE 0 END) AS loss_trades_count_d14,
        SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) AS win_trades_count_d14,
        MIN(CAST(julianday(t.trade_date) - julianday(u.signup_date) AS INTEGER)) AS days_to_first_trade_d14,
        SUM(CASE WHEN t.product IN ('options', 'futures') THEN 1 ELSE 0 END) AS fno_trades_count_d14,
        SUM(CASE WHEN t.product = 'equity_delivery' THEN 1 ELSE 0 END) AS delivery_trades_count_d14
    FROM trades t
    JOIN users u ON t.user_id = u.user_id
    WHERE t.trade_date <= date(u.signup_date, '+14 days')
    GROUP BY t.user_id
),
tickets_d14 AS (
    SELECT
        tk.user_id,
        COUNT(*) AS ticket_count_d14,
        SUM(CASE WHEN tk.category = 'kyc_query' THEN 1 ELSE 0 END) AS kyc_ticket_count_d14,
        SUM(CASE WHEN tk.category = 'funding_delay' THEN 1 ELSE 0 END) AS funding_ticket_count_d14
    FROM support_tickets tk
    JOIN users u ON tk.user_id = u.user_id
    WHERE tk.ticket_date <= date(u.signup_date, '+14 days')
    GROUP BY tk.user_id
)
SELECT
    u.user_id,
    u.signup_date,
    u.city_tier,
    u.age_band,
    u.acquisition_channel,
    CASE
        WHEN u.kyc_completed_date IS NOT NULL AND u.kyc_completed_date <= date(u.signup_date, '+14 days') THEN 1
        ELSE 0
    END AS kyc_completed_d14,
    CASE
        WHEN u.kyc_completed_date IS NOT NULL AND u.kyc_completed_date <= date(u.signup_date, '+14 days')
        THEN CAST(julianday(u.kyc_completed_date) - julianday(u.signup_date) AS INTEGER)
        ELSE NULL
    END AS days_to_kyc,
    CASE WHEN COALESCE(f.funding_count_d14, 0) > 0 THEN 1 ELSE 0 END AS is_funded_d14,
    COALESCE(f.funding_count_d14, 0) AS funding_count_d14,
    COALESCE(f.total_funded_amount_d14, 0.0) AS total_funded_amount_d14,
    f.days_to_first_funding,
    COALESCE(s.session_count_d14, 0) AS session_count_d14,
    COALESCE(s.active_days_d14, 0) AS active_days_d14,
    COALESCE(s.total_screens_viewed_d14, 0) AS total_screens_viewed_d14,
    COALESCE(s.avg_screens_per_session_d14, 0.0) AS avg_screens_per_session_d14,
    COALESCE(s.total_watchlist_adds_d14, 0) AS total_watchlist_adds_d14,
    COALESCE(s.max_watchlist_adds_session_d14, 0) AS max_watchlist_adds_session_d14,
    s.last_session_day_d14,
    COALESCE(t.trade_count_d14, 0) AS trade_count_d14,
    COALESCE(t.total_trade_value_d14, 0.0) AS total_trade_value_d14,
    COALESCE(t.total_realized_pnl_d14, 0.0) AS total_realized_pnl_d14,
    COALESCE(t.worst_trade_pnl_d14, 0.0) AS worst_trade_pnl_d14,
    COALESCE(t.loss_trades_count_d14, 0) AS loss_trades_count_d14,
    COALESCE(t.win_trades_count_d14, 0) AS win_trades_count_d14,
    t.days_to_first_trade_d14,
    COALESCE(t.fno_trades_count_d14, 0) AS fno_trades_count_d14,
    COALESCE(t.delivery_trades_count_d14, 0) AS delivery_trades_count_d14,
    COALESCE(tk.ticket_count_d14, 0) AS ticket_count_d14,
    COALESCE(tk.kyc_ticket_count_d14, 0) AS kyc_ticket_count_d14,
    COALESCE(tk.funding_ticket_count_d14, 0) AS funding_ticket_count_d14
FROM users u
LEFT JOIN funding_d14 f ON u.user_id = f.user_id
LEFT JOIN sessions_d14 s ON u.user_id = s.user_id
LEFT JOIN trades_d14 t ON u.user_id = t.user_id
LEFT JOIN tickets_d14 tk ON u.user_id = tk.user_id
ORDER BY u.user_id;

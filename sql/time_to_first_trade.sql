-- Dormancy rate by time to first trade
-- Analyzes relationship between conversion speed and day 61-90 dormancy.

WITH user_dormancy AS (
    SELECT
        u.user_id,
        u.signup_date,
        CASE WHEN COUNT(a.activity_date) = 0 THEN 1 ELSE 0 END AS is_dormant
    FROM users u
    LEFT JOIN activity a
        ON u.user_id = a.user_id
        AND a.activity_date >= date(u.signup_date, '+61 days')
        AND a.activity_date <= date(u.signup_date, '+90 days')
    GROUP BY u.user_id
),
user_first_trade AS (
    SELECT
        ud.user_id,
        ud.is_dormant,
        MIN(t.trade_date) AS first_trade_date,
        CAST(julianday(MIN(t.trade_date)) - julianday(ud.signup_date) AS INTEGER) AS days_to_trade
    FROM user_dormancy ud
    LEFT JOIN trades t ON ud.user_id = t.user_id
    GROUP BY ud.user_id
),
bucketed AS (
    SELECT
        user_id,
        is_dormant,
        CASE
            WHEN days_to_trade IS NULL THEN 'Never traded'
            WHEN days_to_trade = 0 THEN '0 days (same day)'
            WHEN days_to_trade BETWEEN 1 AND 3 THEN '1-3 days'
            WHEN days_to_trade BETWEEN 4 AND 7 THEN '4-7 days'
            WHEN days_to_trade BETWEEN 8 AND 14 THEN '8-14 days'
            WHEN days_to_trade BETWEEN 15 AND 30 THEN '15-30 days'
            ELSE '31+ days'
        END AS time_bucket,
        CASE
            WHEN days_to_trade = 0 THEN 1
            WHEN days_to_trade BETWEEN 1 AND 3 THEN 2
            WHEN days_to_trade BETWEEN 4 AND 7 THEN 3
            WHEN days_to_trade BETWEEN 8 AND 14 THEN 4
            WHEN days_to_trade BETWEEN 15 AND 30 THEN 5
            WHEN days_to_trade > 30 THEN 6
            ELSE 7
        END AS sort_order
    FROM user_first_trade
)
SELECT
    sort_order,
    time_bucket,
    COUNT(*) AS total_users,
    SUM(is_dormant) AS dormant_users,
    COUNT(*) - SUM(is_dormant) AS active_users,
    ROUND(SUM(is_dormant) * 100.0 / COUNT(*), 1) AS dormancy_rate_pct
FROM bucketed
GROUP BY sort_order, time_bucket
ORDER BY sort_order;

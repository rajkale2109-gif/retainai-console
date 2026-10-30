-- Monthly cohort retention matrix
-- Uses the activity view (sessions + trades) to calculate active users across lifecycle windows.

WITH cohort_activity AS (
    SELECT
        strftime('%Y-%m', u.signup_date) AS cohort_month,
        u.user_id,
        MAX(CASE WHEN a.activity_date >= u.signup_date AND a.activity_date <= date(u.signup_date, '+14 days') THEN 1 ELSE 0 END) AS active_d14,
        MAX(CASE WHEN a.activity_date >= date(u.signup_date, '+15 days') AND a.activity_date <= date(u.signup_date, '+30 days') THEN 1 ELSE 0 END) AS active_d30,
        MAX(CASE WHEN a.activity_date >= date(u.signup_date, '+31 days') AND a.activity_date <= date(u.signup_date, '+60 days') THEN 1 ELSE 0 END) AS active_d60,
        MAX(CASE WHEN a.activity_date >= date(u.signup_date, '+61 days') AND a.activity_date <= date(u.signup_date, '+90 days') THEN 1 ELSE 0 END) AS active_d90
    FROM users u
    LEFT JOIN activity a ON u.user_id = a.user_id
    GROUP BY u.user_id
)
SELECT
    cohort_month,
    COUNT(*) AS cohort_size,
    SUM(active_d14) AS active_d0_14,
    ROUND(SUM(active_d14) * 100.0 / COUNT(*), 1) AS retention_d0_14_pct,
    SUM(active_d30) AS active_d15_30,
    ROUND(SUM(active_d30) * 100.0 / COUNT(*), 1) AS retention_d15_30_pct,
    SUM(active_d60) AS active_d31_60,
    ROUND(SUM(active_d60) * 100.0 / COUNT(*), 1) AS retention_d31_60_pct,
    SUM(active_d90) AS active_d61_90,
    ROUND(SUM(active_d90) * 100.0 / COUNT(*), 1) AS retention_d61_90_pct,
    ROUND((COUNT(*) - SUM(active_d90)) * 100.0 / COUNT(*), 1) AS dormancy_d61_90_pct
FROM cohort_activity
GROUP BY cohort_month
ORDER BY cohort_month;

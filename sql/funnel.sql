-- Conversion funnel: Signup -> KYC -> Funded -> Traded (<= 30 days)
-- Runs strictly via SQLite.

WITH user_stages AS (
    SELECT
        u.user_id,
        u.signup_date,
        CASE WHEN u.kyc_completed_date IS NOT NULL THEN 1 ELSE 0 END AS has_kyc,
        CASE WHEN f.user_id IS NOT NULL THEN 1 ELSE 0 END AS has_funded,
        CASE WHEN t.user_id IS NOT NULL THEN 1 ELSE 0 END AS has_traded_30d
    FROM users u
    LEFT JOIN (
        SELECT DISTINCT user_id FROM funding
    ) f ON u.user_id = f.user_id
    LEFT JOIN (
        SELECT DISTINCT t.user_id
        FROM trades t
        JOIN users u2 ON t.user_id = u2.user_id
        WHERE t.trade_date <= date(u2.signup_date, '+30 days')
    ) t ON u.user_id = t.user_id
)
SELECT
    COUNT(*) AS total_signups,
    SUM(has_kyc) AS completed_kyc,
    ROUND(SUM(has_kyc) * 1.0 / COUNT(*), 4) AS kyc_rate,
    SUM(has_funded) AS funded_users,
    ROUND(SUM(has_funded) * 1.0 / NULLIF(SUM(has_kyc), 0), 4) AS funded_rate_of_kyc,
    ROUND(SUM(has_funded) * 1.0 / COUNT(*), 4) AS funded_rate_overall,
    SUM(has_traded_30d) AS traded_30d_users,
    ROUND(SUM(has_traded_30d) * 1.0 / NULLIF(SUM(has_funded), 0), 4) AS traded_rate_of_funded,
    ROUND(SUM(has_traded_30d) * 1.0 / COUNT(*), 4) AS traded_rate_overall
FROM user_stages;

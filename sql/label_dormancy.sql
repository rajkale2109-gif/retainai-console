-- Ground truth dormancy label calculation
-- Dormant = no login (session) and no trade between day 61 and day 90 after signup.
-- Uses the activity view.

SELECT
    u.user_id,
    CASE
        WHEN COUNT(a.activity_date) = 0 THEN 1
        ELSE 0
    END AS is_dormant
FROM users u
LEFT JOIN activity a
    ON u.user_id = a.user_id
    AND a.activity_date >= date(u.signup_date, '+61 days')
    AND a.activity_date <= date(u.signup_date, '+90 days')
GROUP BY u.user_id
ORDER BY u.user_id;

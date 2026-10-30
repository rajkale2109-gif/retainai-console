"""Synthetic data generation for RetainAI retail broking retention console.

Calibration Targets (from SPEC.md):
- 20,000 users with signups distributed across calendar year 2025.
- Fixed random seed for complete reproducibility.
- About 83% complete KYC.
- About 57% of KYC-completed users add funds (~47.3% of all users).
- About 63% of funded users place a first trade within 30 days of signup.
- About 37% dormant by day 90 (no login and no trade between day 61 and day 90).

Behavioural Rules:
1. Acquisition channel changes user intent:
   - Referral: highest intent, highest KYC/funding rate, lowest dormancy (~22%).
   - Organic: high intent, above-average conversion, low dormancy (~30%).
   - Paid search: baseline benchmark intent, average conversion, moderate dormancy (~38%).
   - Performance ad: impulse intent, below-average conversion, higher dormancy (~46%).
   - Influencer: lowest intent, lowest conversion, highest dormancy (~59%).
2. Realised loss: users who experience an early realised loss (worst trade PnL <= -250)
   suffer higher friction and have higher dormancy.
3. Funding status: users who never fund their account have significantly higher dormancy.
4. Demographics: 3.5% missing values in age_band and city_tier.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.config import (
    AGE_BAND_WEIGHTS,
    AGE_BANDS,
    CHANNEL_INTENT_MULTIPLIERS,
    CHANNEL_WEIGHTS,
    CHANNELS,
    CITY_TIER_WEIGHTS,
    CITY_TIERS,
    MISSING_DEMO_RATE,
    N_USERS,
    PRODUCT_WEIGHTS,
    PRODUCTS,
    RANDOM_SEED,
    SIGNUP_END_DATE,
    SIGNUP_START_DATE,
    TICKET_CATEGORIES,
)


def generate_users(
    n_users: int = N_USERS,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate the users table along with intermediate status masks.

    Returns:
        users_df: DataFrame matching table users(user_id, signup_date, city_tier, age_band, acquisition_channel, kyc_completed_date)
        kyc_mask: boolean array indicating KYC completion
        funded_mask: boolean array indicating account funding
        traded_30d_mask: boolean array indicating first trade placed within 30 days
        is_dormant_arr: boolean array indicating day 61-90 dormancy
    """
    rng = np.random.default_rng(seed)

    user_ids = np.arange(1, n_users + 1, dtype=int)

    # 1. Acquisition channel
    user_channels = rng.choice(CHANNELS, size=n_users, p=CHANNEL_WEIGHTS)

    # 2. Signup dates across 2025
    start_dt = pd.Timestamp(SIGNUP_START_DATE)
    day_offsets = rng.integers(0, 365, size=n_users)
    signup_dates = [start_dt + pd.Timedelta(days=int(d)) for d in day_offsets]

    # 3. Demographics with ~3.5% missingness
    user_ages = rng.choice(AGE_BANDS, size=n_users, p=AGE_BAND_WEIGHTS).astype(object)
    user_cities = rng.choice(CITY_TIERS, size=n_users, p=CITY_TIER_WEIGHTS).astype(object)

    missing_age = rng.random(n_users) < MISSING_DEMO_RATE
    user_ages[missing_age] = None

    missing_city = rng.random(n_users) < MISSING_DEMO_RATE
    user_cities[missing_city] = None

    # 4. KYC completion: Target ~83%
    # Referral has highest KYC rate; influencer has lowest.
    base_kyc_prob = 0.824
    kyc_probs = np.array([
        min(0.98, max(0.40, base_kyc_prob * CHANNEL_INTENT_MULTIPLIERS[c]["kyc"]))
        for c in user_channels
    ])
    kyc_mask = rng.random(n_users) < kyc_probs

    # KYC completion timing: 0 to 4 days after signup
    kyc_days = rng.integers(0, 5, size=n_users)
    kyc_dates: List[Optional[str]] = [
        (signup_dates[i] + pd.Timedelta(days=int(kyc_days[i]))).strftime("%Y-%m-%d")
        if kyc_mask[i] else None
        for i in range(n_users)
    ]

    # 5. Funding: Target ~57% of KYC completed
    base_fund_prob = 0.563
    funded_mask = np.zeros(n_users, dtype=bool)
    for i in range(n_users):
        if kyc_mask[i]:
            p = min(0.95, max(0.20, base_fund_prob * CHANNEL_INTENT_MULTIPLIERS[user_channels[i]]["funding"]))
            funded_mask[i] = rng.random() < p

    # 6. Trades within 30 days: Target ~63% of funded users
    base_trade_prob = 0.628
    traded_30d_mask = np.zeros(n_users, dtype=bool)
    for i in range(n_users):
        if funded_mask[i]:
            p = min(0.95, max(0.20, base_trade_prob * CHANNEL_INTENT_MULTIPLIERS[user_channels[i]]["trade"]))
            traded_30d_mask[i] = rng.random() < p

    # 7. Day 61-90 Dormancy: Target ~37% overall
    # Governed by channel intent, funding status, and early trading activity
    dormant_logits = []
    base_dormancy_logit = -0.85
    for i in range(n_users):
        logit = base_dormancy_logit
        ch = user_channels[i]
        if ch == "referral":
            logit -= 0.60
        elif ch == "organic":
            logit -= 0.28
        elif ch == "paid_search":
            logit += 0.05
        elif ch == "performance_ad":
            logit += 0.35
        elif ch == "influencer":
            logit += 0.80

        if not kyc_mask[i]:
            logit += 0.90
        elif not funded_mask[i]:
            logit += 0.65
        elif not traded_30d_mask[i]:
            logit += 0.30
        else:
            logit -= 0.68

        dormant_logits.append(logit)

    probs = 1.0 / (1.0 + np.exp(-np.array(dormant_logits)))
    is_dormant_arr = rng.random(n_users) < probs

    users_df = pd.DataFrame({
        "user_id": user_ids,
        "signup_date": [dt.strftime("%Y-%m-%d") for dt in signup_dates],
        "city_tier": user_cities,
        "age_band": user_ages,
        "acquisition_channel": user_channels,
        "kyc_completed_date": kyc_dates,
    })

    return users_df, kyc_mask, funded_mask, traded_30d_mask, is_dormant_arr


def generate_funding(
    users_df: pd.DataFrame,
    funded_mask: np.ndarray,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate the funding table for funded users."""
    rng = np.random.default_rng(seed + 1)
    funding_rows = []

    for idx, row in users_df.iterrows():
        if not funded_mask[idx]:
            continue

        u_id = int(row["user_id"])
        kyc_dt = pd.Timestamp(row["kyc_completed_date"])

        # First deposit: 0 to 5 days after KYC
        first_fund_offset = int(rng.integers(0, 6))
        first_fund_date = (kyc_dt + pd.Timedelta(days=first_fund_offset)).strftime("%Y-%m-%d")

        # Initial deposit amount in INR (log-normal distribution with median ~₹8,000)
        # Rounded to nearest 500 or 1000
        raw_amt = float(np.exp(rng.normal(9.0, 0.95)))
        first_amt = max(500.0, round(raw_amt / 500.0) * 500.0)

        funding_rows.append({
            "user_id": u_id,
            "fund_date": first_fund_date,
            "amount": first_amt,
        })

        # 30% of funded users make a second deposit later
        if rng.random() < 0.30:
            second_offset = first_fund_offset + int(rng.integers(10, 45))
            second_fund_date = (kyc_dt + pd.Timedelta(days=second_offset)).strftime("%Y-%m-%d")
            raw_amt_2 = float(np.exp(rng.normal(8.8, 0.9)))
            second_amt = max(500.0, round(raw_amt_2 / 500.0) * 500.0)
            funding_rows.append({
                "user_id": u_id,
                "fund_date": second_fund_date,
                "amount": second_amt,
            })

    return pd.DataFrame(funding_rows)


def generate_trades(
    users_df: pd.DataFrame,
    funded_mask: np.ndarray,
    traded_30d_mask: np.ndarray,
    is_dormant_arr: np.ndarray,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate the trades table.

    Includes early trades (days 0-14) that can generate realised losses <= -250 (Burned segment).
    Dormant users have 0 trades between day 61 and day 90.
    """
    rng = np.random.default_rng(seed + 2)
    trade_rows = []

    for idx, row in users_df.iterrows():
        if not funded_mask[idx]:
            continue

        u_id = int(row["user_id"])
        signup_dt = pd.Timestamp(row["signup_date"])
        is_dormant = bool(is_dormant_arr[idx])
        trades_30d = bool(traded_30d_mask[idx])

        # Users who trade within 30 days
        if trades_30d:
            # First trade between day 1 and 28
            first_day = int(rng.integers(1, 29))
            # Determine number of trades based on user engagement
            n_trades = int(rng.geometric(p=0.35))
            trade_days = [first_day]

            for _ in range(n_trades - 1):
                next_day = trade_days[-1] + int(rng.integers(1, 15))
                # If dormant, user MUST NOT trade in day 61-90
                if is_dormant and (61 <= next_day <= 90):
                    continue
                if next_day > 120:
                    break
                trade_days.append(next_day)

            for day_offset in trade_days:
                t_date = (signup_dt + pd.Timedelta(days=day_offset)).strftime("%Y-%m-%d")
                product = str(rng.choice(PRODUCTS, p=PRODUCT_WEIGHTS))
                trade_val = float(round(rng.uniform(1000, 45000) / 100) * 100)

                # Realized PnL:
                # Early trades (<= 14 days): about 22% experience significant loss (<= -250)
                if day_offset <= 14:
                    if rng.random() < 0.22:
                        pnl = float(-rng.uniform(250, 2400))
                    else:
                        pnl = float(rng.normal(120, 280))
                else:
                    pnl = float(rng.normal(80, 350))

                trade_rows.append({
                    "user_id": u_id,
                    "trade_date": t_date,
                    "product": product,
                    "value": trade_val,
                    "realized_pnl": round(pnl, 2),
                })
        else:
            # A small fraction of funded users who didn't trade in 30 days trade later (day 35-55)
            if rng.random() < 0.15:
                late_day = int(rng.integers(35, 56))
                t_date = (signup_dt + pd.Timedelta(days=late_day)).strftime("%Y-%m-%d")
                product = str(rng.choice(PRODUCTS, p=PRODUCT_WEIGHTS))
                trade_val = float(round(rng.uniform(1000, 25000) / 100) * 100)
                pnl = float(rng.normal(50, 200))
                trade_rows.append({
                    "user_id": u_id,
                    "trade_date": t_date,
                    "product": product,
                    "value": trade_val,
                    "realized_pnl": round(pnl, 2),
                })

    return pd.DataFrame(trade_rows)


def generate_sessions(
    users_df: pd.DataFrame,
    funded_mask: np.ndarray,
    is_dormant_arr: np.ndarray,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate the sessions table.

    Rules:
    - Every user has a session on signup day (day 0).
    - Browser users: unfunded users who add 6+ watchlist items in days 0-14.
    - Dormant users have strictly ZERO sessions between day 61 and day 90.
    - Active users (not dormant) have at least 1 session between day 61 and day 90.
    """
    rng = np.random.default_rng(seed + 3)
    session_rows = []

    for idx, row in users_df.iterrows():
        u_id = int(row["user_id"])
        signup_dt = pd.Timestamp(row["signup_date"])
        is_dormant = bool(is_dormant_arr[idx])
        is_funded = bool(funded_mask[idx])

        # 1. Day 0 session (signup day)
        session_rows.append({
            "user_id": u_id,
            "session_date": signup_dt.strftime("%Y-%m-%d"),
            "screens_viewed": int(rng.integers(5, 18)),
            "watchlist_adds": int(rng.integers(0, 3)),
        })

        # 2. Days 1 to 14 sessions
        # Unfunded "Browser" candidates: designate ~20% of unfunded users to browse heavily
        is_browser_candidate = (not is_funded) and (rng.random() < 0.20)

        n_day14_sessions = int(rng.integers(2, 9)) if (is_funded or is_browser_candidate) else int(rng.integers(0, 3))
        if n_day14_sessions > 0:
            chosen_days = sorted(list(rng.choice(np.arange(1, 15), size=min(14, n_day14_sessions), replace=False)))
            for d in chosen_days:
                s_date = (signup_dt + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d")
                screens = int(rng.integers(4, 26))
                if is_browser_candidate:
                    # High watchlist adds so cumulative >= 6
                    wl_adds = int(rng.integers(2, 6))
                else:
                    wl_adds = int(rng.integers(0, 3))

                session_rows.append({
                    "user_id": u_id,
                    "session_date": s_date,
                    "screens_viewed": screens,
                    "watchlist_adds": wl_adds,
                })

        # 3. Days 15 to 60 sessions
        # Active or moderately engaged users continue logging in
        if rng.random() < (0.75 if not is_dormant else 0.35):
            n_mid_sessions = int(rng.integers(2, 10))
            chosen_mid_days = sorted(list(rng.choice(np.arange(15, 61), size=min(46, n_mid_sessions), replace=False)))
            for d in chosen_mid_days:
                s_date = (signup_dt + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d")
                session_rows.append({
                    "user_id": u_id,
                    "session_date": s_date,
                    "screens_viewed": int(rng.integers(3, 20)),
                    "watchlist_adds": int(rng.integers(0, 2)),
                })

        # 4. Days 61 to 90 sessions (DORMANCY CRITICAL WINDOW)
        if is_dormant:
            # STRICT REQUIREMENT: ZERO sessions and ZERO trades between day 61 and day 90!
            pass
        else:
            # STRICT REQUIREMENT: Active users MUST have at least 1 session between day 61 and day 90
            n_late_sessions = int(rng.integers(1, 8))
            chosen_late_days = sorted(list(rng.choice(np.arange(61, 91), size=min(30, n_late_sessions), replace=False)))
            for d in chosen_late_days:
                s_date = (signup_dt + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d")
                session_rows.append({
                    "user_id": u_id,
                    "session_date": s_date,
                    "screens_viewed": int(rng.integers(3, 22)),
                    "watchlist_adds": int(rng.integers(0, 2)),
                })

    return pd.DataFrame(session_rows)


def generate_support_tickets(
    users_df: pd.DataFrame,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate support tickets table (~12% of users raise a ticket)."""
    rng = np.random.default_rng(seed + 4)
    ticket_rows = []

    for idx, row in users_df.iterrows():
        # ~12% probability of raising a support ticket
        if rng.random() < 0.12:
            u_id = int(row["user_id"])
            signup_dt = pd.Timestamp(row["signup_date"])
            t_offset = int(rng.integers(1, 45))
            t_date = (signup_dt + pd.Timedelta(days=t_offset)).strftime("%Y-%m-%d")
            category = str(rng.choice(TICKET_CATEGORIES))
            ticket_rows.append({
                "user_id": u_id,
                "ticket_date": t_date,
                "category": category,
            })

    return pd.DataFrame(ticket_rows)


def generate_all_data(
    n_users: int = N_USERS,
    seed: int = RANDOM_SEED,
) -> Dict[str, pd.DataFrame]:
    """Generate all 5 synthetic tables and return as dictionary."""
    users_df, kyc_mask, funded_mask, traded_30d_mask, is_dormant_arr = generate_users(n_users, seed)
    funding_df = generate_funding(users_df, funded_mask, seed)
    trades_df = generate_trades(users_df, funded_mask, traded_30d_mask, is_dormant_arr, seed)
    sessions_df = generate_sessions(users_df, funded_mask, is_dormant_arr, seed)
    tickets_df = generate_support_tickets(users_df, seed)

    return {
        "users": users_df,
        "funding": funding_df,
        "trades": trades_df,
        "sessions": sessions_df,
        "support_tickets": tickets_df,
    }


if __name__ == "__main__":
    dfs = generate_all_data()
    for name, df in dfs.items():
        print(f"Generated {name:15s}: {len(df):,} rows")

"""Build SQLite database from synthetic data and create required views and indices."""

import sqlite3
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from src.config import DB_PATH, RAW_DATA_DIR, SQL_DIR
from src.generate_data import generate_all_data


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables, indexes, and views in SQLite."""
    cursor = conn.cursor()

    # Drop existing tables and views if rebuilding
    cursor.executescript("""
        DROP VIEW IF EXISTS activity;
        DROP TABLE IF EXISTS support_tickets;
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS trades;
        DROP TABLE IF EXISTS funding;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            signup_date TEXT NOT NULL,
            city_tier TEXT,
            age_band TEXT,
            acquisition_channel TEXT NOT NULL,
            kyc_completed_date TEXT
        );

        CREATE TABLE funding (
            funding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fund_date TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trade_date TEXT NOT NULL,
            product TEXT NOT NULL,
            value REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            screens_viewed INTEGER NOT NULL,
            watchlist_adds INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE support_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticket_date TEXT NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        -- Activity view: unified union of sessions and trades
        CREATE VIEW activity AS
        SELECT
            user_id,
            session_date AS activity_date,
            'session' AS activity_type
        FROM sessions
        UNION ALL
        SELECT
            user_id,
            trade_date AS activity_date,
            'trade' AS activity_type
        FROM trades;

        -- Indexes for high-performance date window lookups
        CREATE INDEX idx_users_signup ON users(signup_date);
        CREATE INDEX idx_funding_user_date ON funding(user_id, fund_date);
        CREATE INDEX idx_trades_user_date ON trades(user_id, trade_date);
        CREATE INDEX idx_sessions_user_date ON sessions(user_id, session_date);
        CREATE INDEX idx_tickets_user_date ON support_tickets(user_id, ticket_date);
    """)
    conn.commit()


def populate_db(conn: sqlite3.Connection, dfs: Dict[str, pd.DataFrame]) -> None:
    """Populate database tables with generated DataFrames."""
    for table_name, df in dfs.items():
        df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.commit()


def run_sql_file(conn: sqlite3.Connection, sql_path: Path) -> pd.DataFrame:
    """Execute a SQL file via SQLite and return results as a DataFrame."""
    with open(sql_path, "r", encoding="utf-8") as f:
        query = f.read()
    return pd.read_sql_query(query, conn)


def print_stage_2_report(conn: sqlite3.Connection) -> None:
    """Print the required Stage 2 validation report."""
    cursor = conn.cursor()

    print("=" * 72)
    print("STAGE 2: DATA AND DATABASE VALIDATION REPORT")
    print("=" * 72)

    # 1. Row counts per table
    tables = ["users", "funding", "trades", "sessions", "support_tickets"]
    print("\n1. Row Counts per Table:")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cursor.fetchone()[0]
        print(f"   - {t:18s}: {cnt:>8,} rows")

    # 2. Funnel verification
    print("\n2. Onboarding Funnel (from sql/funnel.sql via SQLite):")
    funnel_df = run_sql_file(conn, SQL_DIR / "funnel.sql")
    f_row = funnel_df.iloc[0]
    total = f_row["total_signups"]
    kyc_cnt = f_row["completed_kyc"]
    kyc_pct = f_row["kyc_rate"] * 100
    fund_cnt = f_row["funded_users"]
    fund_kyc_pct = f_row["funded_rate_of_kyc"] * 100
    fund_tot_pct = f_row["funded_rate_overall"] * 100
    trade_cnt = f_row["traded_30d_users"]
    trade_fund_pct = f_row["traded_rate_of_funded"] * 100
    trade_tot_pct = f_row["traded_rate_overall"] * 100

    print(f"   - Signups           : {total:>6,} users (100.0%)")
    print(f"   - Completed KYC     : {kyc_cnt:>6,} users ({kyc_pct:5.2f}% vs target 83.0%, gap: {kyc_pct - 83.0:+.2f} pts)")
    print(f"   - Funded Accounts   : {fund_cnt:>6,} users ({fund_kyc_pct:5.2f}% of KYC vs target 57.0%, gap: {fund_kyc_pct - 57.0:+.2f} pts | {fund_tot_pct:5.2f}% overall)")
    print(f"   - Traded in 30 Days : {trade_cnt:>6,} users ({trade_fund_pct:5.2f}% of Funded vs target 63.0%, gap: {trade_fund_pct - 63.0:+.2f} pts | {trade_tot_pct:5.2f}% overall)")

    # 3. Dormancy verification
    print("\n3. Dormancy Rate (from sql/label_dormancy.sql via SQLite):")
    dorm_df = run_sql_file(conn, SQL_DIR / "label_dormancy.sql")
    dormant_cnt = dorm_df["is_dormant"].sum()
    total_users = len(dorm_df)
    dorm_rate = (dormant_cnt / total_users) * 100.0
    print(f"   - Day 61-90 Dormancy: {dormant_cnt:>6,} users ({dorm_rate:5.2f}% vs target 37.0%, gap: {dorm_rate - 37.0:+.2f} pts)")

    # 4. Dormancy by Acquisition Channel
    print("\n4. Day 61-90 Dormancy by Acquisition Channel (via SQLite):")
    channel_sql = """
        WITH dormancy AS (
            SELECT
                u.user_id,
                u.acquisition_channel,
                CASE WHEN COUNT(a.activity_date) = 0 THEN 1 ELSE 0 END AS is_dormant
            FROM users u
            LEFT JOIN activity a
                ON u.user_id = a.user_id
                AND a.activity_date >= date(u.signup_date, '+61 days')
                AND a.activity_date <= date(u.signup_date, '+90 days')
            GROUP BY u.user_id
        )
        SELECT
            acquisition_channel,
            COUNT(*) AS users,
            SUM(is_dormant) AS dormant_users,
            ROUND(SUM(is_dormant) * 100.0 / COUNT(*), 2) AS dormancy_rate_pct
        FROM dormancy
        GROUP BY acquisition_channel
        ORDER BY dormancy_rate_pct ASC;
    """
    cursor.execute(channel_sql)
    for row in cursor.fetchall():
        ch, u_cnt, d_cnt, d_pct = row
        print(f"   - {ch:16s}: {u_cnt:>6,} users, {d_cnt:>5,} dormant ({d_pct:5.2f}%)")

    # 5. Missing values check
    print("\n5. Missing Values Check (Target: 3-4% as per SPEC.md):")
    cursor.execute("SELECT COUNT(*) FROM users WHERE city_tier IS NULL")
    missing_city = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE age_band IS NULL")
    missing_age = cursor.fetchone()[0]
    print(f"   - Missing city_tier : {missing_city:>5,} ({missing_city * 100.0 / total_users:.2f}%)")
    print(f"   - Missing age_band  : {missing_age:>5,} ({missing_age * 100.0 / total_users:.2f}%)")

    # 6. Gap analysis against targets
    print("\n6. Target Comparison & Discrepancy Check:")
    gaps = [
        ("KYC completion rate", kyc_pct, 83.0),
        ("Funded of KYC rate", fund_kyc_pct, 57.0),
        ("Traded of Funded in 30d", trade_fund_pct, 63.0),
        ("Overall dormancy rate", dorm_rate, 37.0),
    ]
    all_within_threshold = True
    for metric_name, actual, target in gaps:
        gap = abs(actual - target)
        status = "PASS (<3 pts)" if gap <= 3.0 else "EXCEED (>3 pts)"
        print(f"   - {metric_name:25s}: Actual {actual:5.2f}% | Target {target:5.2f}% | Gap: {gap:4.2f} pts -> {status}")
        if gap > 3.0:
            all_within_threshold = False

    if all_within_threshold:
        print("\nAll metrics are well within the 3.0 percentage point target threshold.")
    else:
        print("\nWarning: One or more metrics exceed the 3.0 percentage point threshold.")
    print("=" * 72)


def build_database(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Orchestrate data generation and database build."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating synthetic dataset (20,000 users, seed 42)...")
    dfs = generate_all_data()

    print(f"Building SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    init_db(conn)
    populate_db(conn, dfs)

    return conn


if __name__ == "__main__":
    conn = build_database()
    print_stage_2_report(conn)
    conn.close()

"""Configuration constants, business rules, and segment parameters for RetainAI."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DB_PATH = RAW_DATA_DIR / "retainai.db"
SCORES_PATH = PROCESSED_DATA_DIR / "scores.csv"
METRICS_PATH = PROCESSED_DATA_DIR / "metrics.json"
SQL_DIR = BASE_DIR / "sql"

# Synthetic Data Calibration
RANDOM_SEED = 42
N_USERS = 20000
SIGNUP_START_DATE = "2025-01-01"
SIGNUP_END_DATE = "2025-12-31"

# Target Calibration Rates (from SPEC.md)
TARGET_KYC_RATE = 0.83                   # ~83% complete KYC
TARGET_FUNDED_OF_KYC_RATE = 0.57         # ~57% of KYC users add funds (~47.3% of total)
TARGET_TRADED_OF_FUNDED_30D_RATE = 0.63  # ~63% of funded place first trade in 30 days
TARGET_DORMANCY_RATE = 0.37              # ~37% dormant by day 90

# Time Windows (days after signup)
PREDICTION_DAY_WINDOW = 14               # Predict at day 14 using behaviour up to day 14
DORMANCY_START_DAY = 61                  # Day 61 start of dormancy window
DORMANCY_END_DAY = 90                    # Day 90 end of dormancy window

# Train / Test Temporal Cutoff
TRAIN_TEST_SPLIT_DATE = "2025-10-01"     # Signups before this date are train, later are test

# Unit Economics
CONTACT_COST_INR = 15.0                  # Direct cost to contact one user in INR

# Acquisition Channels and Intent Hierarchy
# Referral is highest intent; influencer is lowest intent.
CHANNELS = ["referral", "organic", "paid_search", "performance_ad", "influencer"]
CHANNEL_WEIGHTS = [0.20, 0.25, 0.25, 0.18, 0.12]
CHANNEL_INTENT_MULTIPLIERS = {
    "referral": {"kyc": 1.15, "funding": 1.20, "trade": 1.15, "dormancy": 0.68},
    "organic": {"kyc": 1.08, "funding": 1.08, "trade": 1.08, "dormancy": 0.82},
    "paid_search": {"kyc": 1.00, "funding": 1.00, "trade": 1.00, "dormancy": 1.00},
    "performance_ad": {"kyc": 0.92, "funding": 0.90, "trade": 0.90, "dormancy": 1.15},
    "influencer": {"kyc": 0.80, "funding": 0.72, "trade": 0.75, "dormancy": 1.45},
}

# Demographics
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_BAND_WEIGHTS = [0.28, 0.42, 0.18, 0.08, 0.04]

CITY_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
CITY_TIER_WEIGHTS = [0.45, 0.35, 0.20]

# Missing value probabilities for demographics (3-4% as per SPEC.md)
MISSING_DEMO_RATE = 0.035

# Trade Products
PRODUCTS = ["equity_delivery", "equity_intraday", "etf", "options", "futures"]
PRODUCT_WEIGHTS = [0.52, 0.22, 0.14, 0.08, 0.04]

# Ticket Categories
TICKET_CATEGORIES = ["kyc_query", "funding_delay", "app_issue", "order_query", "statement_request"]


@dataclass(frozen=True)
class SegmentDef:
    """Segment configuration definition."""
    name: str
    action: str
    channel: str
    message: str
    save_rate: float
    lifetime_value: float


# Segment Playbook Definitions (SPEC.md)
SEGMENT_PLAYBOOK: Dict[str, SegmentDef] = {
    "Burned": SegmentDef(
        name="Burned",
        action="Offer personalized risk review and capital preservation guide",
        channel="Relationship manager call",
        message="We noticed your recent trading volatility. Let our senior research team walk you through risk management and hedging techniques.",
        save_rate=0.18,
        lifetime_value=2200.0,
    ),
    "Hesitant": SegmentDef(
        name="Hesitant",
        action="Send guided first-trade demo and starter ETF list",
        channel="WhatsApp",
        message="Your account is funded and ready. Place your first zero-brokerage ETF investment in under 2 minutes with our starter guide.",
        save_rate=0.24,
        lifetime_value=1800.0,
    ),
    "Browser": SegmentDef(
        name="Browser",
        action="Send market alert on watchlist stocks with instant funding link",
        channel="In-app push",
        message="Stocks on your watchlist are moving today. Complete UPI instant verification to take advantage of market movements.",
        save_rate=0.15,
        lifetime_value=1200.0,
    ),
    "Unfunded": SegmentDef(
        name="Unfunded",
        action="Send instant UPI onboarding nudge with zero AMC benefit",
        channel="SMS",
        message="Start your investment journey with ₹100. Seamless 1-click UPI funding with zero account maintenance charges for year 1.",
        save_rate=0.08,
        lifetime_value=800.0,
    ),
    "Monitor": SegmentDef(
        name="Monitor",
        action="Deliver weekly curated market intelligence digest",
        channel="Email",
        message="Here is your weekly market summary, macro sector trends, and top gainers from the RetainAI research team.",
        save_rate=0.04,
        lifetime_value=1500.0,
    ),
}

# Design Tokens (SPEC.md)
COLOR_CANVAS = "#F5F6F8"
COLOR_SURFACE = "#FFFFFF"
COLOR_INK = "#17212B"
COLOR_PETROL = "#0E5A6B"
COLOR_MUTED_RED = "#A63D40"
COLOR_AMBER = "#B7791F"
FONT_FAMILY = "Public Sans, -apple-system, BlinkMacSystemFont, sans-serif"

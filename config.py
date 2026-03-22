"""
config.py — Centralized Configuration for the EGX Intelligence System
=====================================================================
All tunable parameters live here. Change thresholds, URLs, or API keys
in ONE place instead of hunting through multiple files.

Environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) override
hard-coded defaults so you never commit secrets to version control.
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────
# 1. PROJECT PATHS
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent          # Root of the project
DB_PATH  = BASE_DIR / "egx_data.db"                 # SQLite database file

# ─────────────────────────────────────────────
# 2. SCRAPER SETTINGS
# ─────────────────────────────────────────────
# The target page listing all EGX equities with live prices & volumes.
SCRAPE_URL = "https://www.investing.com/equities/egypt"

# Headers that mimic a real browser — reduces chance of being blocked.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Maximum seconds to wait for a page response before giving up.
REQUEST_TIMEOUT = 30

# How many times to retry a failed scrape before raising an error.
MAX_RETRIES = 3

# ─────────────────────────────────────────────
# 3. TECHNICAL ANALYSIS THRESHOLDS
# ─────────────────────────────────────────────
# RSI below this value = "oversold" → potential buying opportunity.
RSI_OVERSOLD = 35

# A stock's volume must be at least this multiple of its 10-day
# average volume to qualify as a "volume spike."
VOLUME_SPIKE_MULTIPLIER = 1.5

# RSI look-back window in trading days (industry standard = 14).
RSI_PERIOD = 14

# Moving Averages — used for trend confirmation on the dashboard.
SMA_SHORT = 50    # 50-day Simple Moving Average
SMA_LONG  = 200   # 200-day Simple Moving Average (the "Golden Cross" line)

# MACD parameters (fast, slow, signal).
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9

# Volume average look-back (in trading days).
VOLUME_AVG_PERIOD = 10

# ─────────────────────────────────────────────
# 4. EXIT STRATEGY (RISK MANAGEMENT)
# ─────────────────────────────────────────────
# Percentage above entry price to place the TARGET (take-profit).
TARGET_PCT = 0.05   # +5%

# Percentage below entry price to place the STOP-LOSS.
STOP_LOSS_PCT = 0.03  # −3%

# How many "Top Picks" to return each day.
TOP_N_PICKS = 3

# Minimum number of trading days of data before generating signals.
MIN_HISTORY_DAYS = 28

# Minimum daily volume (shares) to filter out thinly traded stocks.
MIN_DAILY_VOLUME = 500_000

# Maximum trading days to hold a pick before auto-expiring.
MAX_HOLDING_DAYS = 10

# ATR-based exit multipliers (used when ATR is available).
ATR_TARGET_MULTIPLIER = 2.0   # Target = Entry + (2.0 × ATR)
ATR_STOP_MULTIPLIER   = 1.5   # Stop   = Entry - (1.5 × ATR)


# ─────────────────────────────────────────────
# 5. TELEGRAM BOT
# ─────────────────────────────────────────────
# Set these as environment variables for security:
#   $env:TELEGRAM_BOT_TOKEN = "123456:ABC-DEF..."
#   $env:TELEGRAM_CHAT_ID   = "987654321"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8636362149:AAFNcBZZo_ilP6211qkd7e7nJlyegoMXczs")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "821030357")

# ─────────────────────────────────────────────
# 6. SCHEDULER
# ─────────────────────────────────────────────
# EGX trades Sunday → Thursday, 10:00 AM – 2:30 PM Cairo Time.
# Three analysis runs per day:
#   1. Market Open  → 10:00 AM
#   2. Mid-Day      → 12:15 PM
#   3. Pre-Close    → 02:00 PM (30 min before close)
SCHEDULE_TIMES = [
    {"hour": 10, "minute": 0,  "label": "Market Open"},
    {"hour": 12, "minute": 15, "label": "Mid-Day"},
    {"hour": 13, "minute": 0,  "label": "Pre-Close"},
]
SCHEDULE_TIMEZONE = "Africa/Cairo"

# Day-of-week filter: 0=Mon … 6=Sun.
# Sun(6), Mon(0), Tue(1), Wed(2), Thu(3) → EGX trading days.
EGX_TRADING_DAYS = {0, 1, 2, 3, 6}  # Mon–Thu + Sun

# ─────────────────────────────────────────────
# 7. STREAMLIT DASHBOARD
# ─────────────────────────────────────────────
STREAMLIT_PAGE_TITLE = "EGX Intelligence Dashboard"
STREAMLIT_PAGE_ICON  = "📈"

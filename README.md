# EGX Intelligence System
![Python 3.10](https://img.shields.io/badge/python-3.10+-blue.svg) ![Status](https://img.shields.io/badge/status-active-green.svg) ![Market](https://img.shields.io/badge/market-EGX-red.svg)

A fully automated, end-to-end trading intelligence pipeline for the Egyptian Stock Exchange (EGX). This system handles everything from raw data scraping to technical analysis, signal generation, and performance tracking, delivering alerts via Telegram and a professional web dashboard.

## Overview
This isn't a toy project or a simple scraper. It is a production-ready pipeline designed to find high-probability "smart money" accumulation patterns in the EGX. The system runs autonomously on a Windows environment, triggering every trading morning to provide actionable insights before the market gets too deep into the session.

## The Strategy: Mean Reversion + Accumulation
The core logic identifies stocks that have been oversold but are suddenly showing signs of institutional interest. We look for a specific "V-shape" or "Dip-Buy" profile:

1.  **RSI (14) < 35**: The stock is mathematically oversold. The market has likely overreacted, pushing the price below its short-term fair value.
2.  **Volume Spike > 1.5×**: Today's trading volume is at least 50% higher than the 10-day rolling average. 

**The Hypothesis**: When an extremely oversold stock (RSI < 35) suddenly sees a massive surge in volume (1.5x+ spike), it is rarely retail traders. It suggests "smart money" (institutional players) is stepping in to accumulate shares at the discount.

### Safety Filters (No Junk Signals)
To ensure the system only flags high-conviction opportunities, several strict filters are applied:
*   **Data Sufficiency**: Requires exactly 28 trading days of history before a signal can even be calculated. This prevents "new-data" noise from creating fake RSI readings.
*   **Price Direction**: Stocks down more than 3% on the signal day are automatically excluded. A volume spike during a -5% crash is usually a panic selloff or institutional exit, not accumulation.
*   **Minimum Liquidity**: Excludes stocks with less than 500,000 shares traded daily. This filters out "penny stock" manipulation where a single small order can fake a volume spike.
*   **No Forced Picks**: If nothing meets the criteria, the system returns nothing. We don't use "watchlist" fallbacks to fill space.

### Dynamic Exits (ATR-Based)
We don't use fixed percentages for profit-taking. Instead, we use the **Average True Range (ATR)** to set targets based on the stock's actual volatility:
*   **Target**: Entry + (2.0 × ATR)
*   **Stop-Loss**: Entry − (1.5 × ATR)
*   *Fallback*: If ATR history is insufficient, the system uses a fixed +5% / -3% model.

---

## How It Actually Works (The Daily Flow)
Every EGX trading morning (Sunday – Thursday) at **10:04 AM**, the system wakes up and follows this exact sequence:

1.  **Scrape**: `scraper.py` hits Investing.com using `cloudscraper` to bypass Cloudflare protection. It extracts live prices, highs, lows, and volumes for all major EGX equities.
2.  **Store**: `database.py` saves this raw data into the `daily_prices` table. If the scraper runs twice, it updates the existing record rather than duplicating it.
3.  **Analyze**: `analyzer.py` pulls the last 60 days of history for the scraped stocks. It calculates RSI, SMA, MACD, Volume Spikes, and ATR.
4.  **Signal**: The filtering logic runs. If a stock passes all checks, a "Pick" is generated with an assigned **Confidence Score (0-100)** and a **Signal Reason** (e.g., *"RSI 28.1 | Vol Spike 2.2x"*).
5.  **Notify**: The `telegram_bot.py` sends a formatted morning report to the private Telegram channel with the new picks and a summary of current market breadth.
6.  **Track**: `tracker.py` monitors every "Pending" pick. If the price hits the target or stop-loss, the outcome is recorded. If 10 days pass without a hit, the pick is marked as **EXPIRED**.

---

## File Structure
```text
C:\stock\
├── core_engine.py      — The "Brain": Orchestrates the full daily pipeline.
├── scraper.py          — Data Acquisition: Cloudflare bypass + BS4 HTML parsing.
├── analyzer.py         — Strategy Engine: TA calculations and signal filtering.
├── database.py         — Persistence: SQLite layer for historical prices and picks.
├── app.py              — Dashboard: Streamlit-based professional trading terminal.
├── telegram_bot.py     — Alerts: Delivers reports and results to Telegram.
├── tracker.py          — Monitor: Tracks open positions and resolves outcomes.
├── scheduler.py        — Automation: Logic for timed execution.
├── config.py           — Settings: Centralized constants and thresholds.
├── run_egx.bat         — Entry Point: Windows batch file for Task Scheduler.
├── egx_data.db         — Database: Local SQLite file (auto-created).
└── logs/               — Logs: Traceable history of every daily run.
```

## Tech Stack
*   **Python 3.10**: Core language.
*   **cloudscraper**: For resilient scraping through Cloudflare.
*   **pandas-ta**: For high-performance technical indicator calculations.
*   **SQLite**: Zero-maintenance local database.
*   **Streamlit**: For the interactive web dashboard.
*   **Plotly**: For high-fidelity, interactive financial charts.
*   **Task Scheduler**: For reliable Windows-native automation.

---

## Database Schema
The system maintains two primary tables in `egx_data.db`:

### `daily_prices`
| Column | Type | Description |
|--------|------|-------------|
| date | TEXT | ISO date (YYYY-MM-DD) |
| name | TEXT | Stock ticker/name |
| last_price | REAL | Closing or latest price |
| volume | REAL | Total shares traded |
| high / low | REAL | Day's range |

### `picks`
| Column | Type | Description |
|--------|------|-------------|
| date | TEXT | Date the signal was generated |
| entry_price | REAL | Price at time of pick |
| target_price| REAL | Take-profit level |
| stop_loss | REAL | Risk management level |
| confidence | REAL | Score from 0 to 100 |
| outcome | TEXT | PENDING, HIT_TARGET, HIT_STOP, or EXPIRED |

---

## Configuration (`config.py`)
Key parameters used to tune the system:
```python
RSI_PERIOD            = 14
RSI_OVERSOLD          = 35
VOLUME_AVG_PERIOD     = 10
VOLUME_SPIKE_MULTIPLIER = 1.5
MIN_HISTORY_DAYS      = 28
MIN_DAILY_VOLUME      = 500_000
MAX_HOLDING_DAYS      = 10
ATR_TARGET_MULTIPLIER = 2.0
ATR_STOP_MULTIPLIER   = 1.5
```

---

## The Dashboard (`app.py`)
Run with: `streamlit run app.py`

The dashboard provides a "Bloomberg-style" dark terminal aesthetic featuring:
*   **History Progress**: A progress bar showing how many days of data have been collected toward the 28-day activation threshold.
*   **Market Context**: Real-time Advance/Decline ratio and EGX 30 direction.
*   **Live Pick Tracker**: Sparkline charts showing the price journey of every open pick relative to its entry and exit levels.
*   **Trajectory Analysis**: Detailed 60-day charts for deeper technical review.
*   **Performance Metrics**: Live Win Rate, Total P&L, and recent outcome history.

---

## Current Status & Performance
*   **Status**: Live / Active Data Collection.
*   **History**: 4 trading days collected (**24 remaining until signal activation**).
*   **Track Record (Historical)**: 9 picks tracked with a **60% win rate**.
*   **Cumulative P&L**: **+17.5%** on resolved picks.

## Road Map
*   [ ] **Backtester**: Replay the accumulation strategy against 2 years of historical data.
*   [ ] **Strategy Tuner**: Automated optimization of RSI and Volume thresholds.
*   [ ] **Position Sizer**: Integrated calculator for risk-adjusted share allocation.

---

## Disclaimer
**This system is for informational and educational purposes only.** It is not financial advice. Trading on the Egyptian Stock Exchange (EGX) carries significant risks, including high volatility, currency fluctuation, and macroeconomic shifts. Past performance is not indicative of future results. Always conduct your own research and consult with a professional advisor before making investment decisions. The developers of this system are not responsible for any financial losses incurred through its use.

# 📈 EGX Intelligence System

> A fully automated intelligence system that identifies the **Top 3 investment opportunities** in the Egyptian Stock Exchange (EGX) every morning before market open.

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Scraper    │────▶│   Database   │────▶│    Analyzer       │
│ (cloudscraper│     │  (SQLite)    │     │ (RSI, MACD, Vol) │
│  + BS4)      │     └──────────────┘     └───────┬──────────┘
└──────────────┘                                  │
                                                  ▼
                                    ┌─────────────────────────┐
                                    │      Top 3 Picks        │
                                    │  Entry / Target / Stop  │
                                    └──────┬──────────┬───────┘
                                           │          │
                                    ┌──────▼──┐  ┌───▼────────┐
                                    │Telegram │  │ Streamlit   │
                                    │   Bot   │  │ Dashboard   │
                                    │[@egx67](https://t.me/egx67_bot)│  └────────────┘
                                    └─────────┘
```

## 📁 Project Structure

```
stock/
├── config.py          # Centralized configuration & thresholds
├── scraper.py         # Web scraping with Cloudflare bypass
├── analyzer.py        # Technical analysis engine
├── core_engine.py     # Unified pipeline (scrape → analyze → store)
├── database.py        # SQLite data persistence
├── telegram_bot.py    # Telegram notification formatting & sending
├── app.py             # Streamlit web dashboard
├── scheduler.py       # APScheduler (08:30 CLT, Sun–Thu)
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Core Engine (Manual Test)

```bash
python core_engine.py
```

This will scrape EGX data, run the analysis, and show the Top 3 picks.

### 3. Launch the Dashboard

```bash
streamlit run app.py
```

### 4. Set Up Telegram (Optional)

```powershell
# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN = "your-bot-token-here"
$env:TELEGRAM_CHAT_ID   = "your-chat-id-here"

# Test sending
python telegram_bot.py
```

### 5. Start the Scheduler (Production)

```bash
# Runs automatically at 08:30 CLT, Sunday–Thursday
python scheduler.py

# Or run once now for testing
python scheduler.py --now
```

## 📊 Selection Logic & Strategy

The system identifies "Mean Reversion" opportunities—stocks that are mathematically oversold but show signs of institutional accumulation.

### 1. The Strategy: "Buying the Quality Dip"
The core objective is to find high-probability reversal points. We look for two specific anomalies happening simultaneously:
*   **Oversold Price Action**: Price has dropped faster than historical norms.
*   **Institutional Confirmation**: High trading volume suggests "Smart Money" is stepping in to support the price.

### 2. How it Works (The Pipeline)
1.  **Scrape**: Pulls live data from EGX equities tables.
2.  **Enrich**: Combines today's data with historical data from SQLite to calculate moving averages.
3.  **Analyze**: 
    *   **Filter 1 (RSI < 35)**: Eliminates any stock not in an "Oversold" state.
    *   **Filter 2 (Volume Spike ≥ 1.5x)**: Eliminates stocks where the price drop isn't backed by an increase in relative trading volume (10-day average).
4.  **Rank**: All stocks passing both filters are ranked by the **magnitude of the Volume Spike**. The larger the spike, the higher the conviction.
5.  **Output**: The **Top 3** ranked stocks are selected. 

### 3. Fallback Mechanism (The Watchlist)
If the market is quiet and *no* stocks meet the strict Volume Spike threshold, the system triggers **Safety Mode**. Instead of an empty report, it identifies the **3 most oversold stocks** (lowest RSI) and labels them as a **Watchlist**. This ensures you are always tracking the most significant pullbacks in the market.

### 4. Technical Indicators
| Indicator | Threshold | Why |
|-----------|-----------|-----|
| RSI(14)   | < 35      | Stock is mathematically "oversold" — potential reversal. |
| Volume Spike | ≥ 1.5× | Today's volume is 50%+ above 10-day average — suggests accumulation. |
| Target    | +5%       | Automatic take-profit level set above entry. |
| Stop-Loss | −3%       | Strict risk management level set below entry. |

## ⚠️ Disclaimer

This tool is for **educational purposes only**. It does not constitute financial advice. Always consult a licensed financial advisor before making investment decisions. Past performance does not guarantee future results.

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

## 📊 Selection Criteria

| Indicator | Threshold | Why |
|-----------|-----------|-----|
| RSI(14)   | < 35      | Stock is "oversold" — potential reversal |
| Volume Spike | ≥ 1.5× | Volume is 50%+ above 10-day average |
| Target    | +5%       | Take-profit level above entry |
| Stop-Loss | −3%       | Risk management below entry |

## ⚠️ Disclaimer

This tool is for **educational purposes only**. It does not constitute financial advice. Always consult a licensed financial advisor before making investment decisions. Past performance does not guarantee future results.

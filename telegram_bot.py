"""
telegram_bot.py — Notification Layer for the EGX Intelligence System
=====================================================================
Formats the daily Top 3 picks into a clean Markdown report and sends
it to your Telegram chat.

SETUP (one-time):
    1. Search for @BotFather on Telegram.
    2. Send /newbot and follow the prompts to get your BOT TOKEN.
    3. Send a message to your new bot, then visit:
         https://api.telegram.org/bot<TOKEN>/getUpdates
       to find your CHAT ID.
    4. Set environment variables:
         $env:TELEGRAM_BOT_TOKEN = "123456:ABC-DEF..."
         $env:TELEGRAM_CHAT_ID   = "987654321"

WHY python-telegram-bot?
    It's the most popular, well-maintained async Telegram library
    for Python.  Version 20+ uses asyncio natively.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)


def format_report(picks: List[Dict], report_date: Optional[str] = None) -> str:
    """
    Format the picks list into a beautiful Telegram Markdown message.

    Example output:
    ┌─────────────────────────────────────┐
    │ 🏆 EGX Morning Report — 2026-03-08 │
    │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
    │                                     │
    │ 1️⃣  COMI                            │
    │    💰 Entry:  42.10 EGP             │
    │    🎯 Target: 44.21 EGP (+5.0%)     │
    │    🛑 Stop:   40.84 EGP (-3.0%)     │
    │    📊 RSI: 28.30 | Vol Spike: 2.1×  │
    │    📈 Signal: Strong Signal          │
    │ ─────────────────────────────────── │
    │ ...                                 │
    └─────────────────────────────────────┘
    """
    today = report_date or date.today().isoformat()

    # Header
    lines = [
        f"🏆 *EGX Morning Report — {today}*",
        "━" * 30,
        "",
    ]

    if not picks:
        lines.append("⚠️ No strong signals detected today.")
        lines.append("The market may be in a consolidation phase.")
        lines.append("")
        lines.append("_Stay disciplined. Not every day is a trading day._")
        return "\n".join(lines)

    # Emoji numbers for ranking.
    rank_emoji = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}

    for i, pick in enumerate(picks, 1):
        emoji = rank_emoji.get(i, f"{i}.")
        name  = pick.get("Name", "Unknown")
        entry = pick.get("Entry", 0)
        target = pick.get("Target", 0)
        stop   = pick.get("Stop_Loss", 0)
        rsi    = pick.get("RSI", 0)
        spike  = pick.get("Volume_Spike", 1.0)
        signal = pick.get("Signal_Type", "Signal")
        change = pick.get("Change_Pct", 0)

        # Calculate % distance for display.
        target_pct = ((target / entry) - 1) * 100 if entry else 0
        stop_pct   = ((stop / entry) - 1) * 100 if entry else 0

        lines.extend([
            f"{emoji}  *{name}*",
            f"    💰 Entry:  `{entry:.2f}` EGP",
            f"    🎯 Target: `{target:.2f}` EGP (+{target_pct:.1f}%)",
            f"    🛑 Stop:   `{stop:.2f}` EGP ({stop_pct:.1f}%)",
            f"    📊 RSI: `{rsi:.1f}` \\| Vol Spike: `{spike:.1f}×`",
            f"    📈 Signal: _{signal}_ \\| Chg: `{change:+.2f}%`",
        ])

        if i < len(picks):
            lines.append("─" * 30)

        lines.append("")

    # Footer
    lines.extend([
        "━" * 30,
        "⏰ _Generated at " + datetime.now().strftime("%H:%M CLT") + "_",
        "⚠️ _This is NOT financial advice. Always DYOR._",
    ])

    return "\n".join(lines)


async def send_telegram_message(text: str) -> bool:
    """
    Send a Markdown-formatted message to the configured Telegram chat.

    Returns True on success, False on failure.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.error(
            "Telegram credentials missing! Set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_CHAT_ID as environment variables."
        )
        return False

    try:
        from telegram import Bot
        from telegram.constants import ParseMode

        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info("✅ Telegram report sent successfully.")
        return True

    except ImportError:
        logger.error(
            "python-telegram-bot not installed. "
            "Run: pip install python-telegram-bot"
        )
        # Fallback: try sending via raw HTTP (no dependency needed).
        return await _send_via_http(text)

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        # Try the HTTP fallback.
        return await _send_via_http(text)


async def _send_via_http(text: str) -> bool:
    """
    Fallback: Send the message via raw HTTP POST to the Telegram API.
    This works even without the python-telegram-bot package.
    """
    import urllib.request
    import urllib.parse
    import json

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                logger.info("✅ Telegram report sent via HTTP fallback.")
                return True
            else:
                logger.error(f"Telegram HTTP response: {resp.status}")
                return False
    except Exception as e:
        logger.error(f"HTTP fallback also failed: {e}")
        return False


async def send_report(picks: List[Dict], report_date: Optional[str] = None) -> bool:
    """
    High-level function: format the picks + send to Telegram.
    This is what the scheduler calls.
    """
    report = format_report(picks, report_date)
    logger.info(f"Report preview:\n{report}")
    return await send_telegram_message(report)


def send_report_sync(picks: List[Dict], report_date: Optional[str] = None) -> bool:
    """
    Synchronous wrapper for send_report().
    Use this when calling from non-async code (e.g., the scheduler).
    """
    return asyncio.run(send_report(picks, report_date))


# ─────────────────────────────────────────────────────────────
# CLI quick-test: `python telegram_bot.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test with dummy picks.
    test_picks = [
        {
            "Name": "COMI",
            "Entry": 42.10,
            "Target": 44.21,
            "Stop_Loss": 40.84,
            "RSI": 28.30,
            "Volume_Spike": 2.1,
            "Change_Pct": -1.25,
            "Signal_Type": "Strong Signal",
        },
        {
            "Name": "HRHO",
            "Entry": 15.50,
            "Target": 16.28,
            "Stop_Loss": 15.04,
            "RSI": 31.50,
            "Volume_Spike": 1.8,
            "Change_Pct": -2.10,
            "Signal_Type": "Strong Signal",
        },
        {
            "Name": "SWDY",
            "Entry": 8.75,
            "Target": 9.19,
            "Stop_Loss": 8.49,
            "RSI": 33.20,
            "Volume_Spike": 1.6,
            "Change_Pct": -0.80,
            "Signal_Type": "Watchlist",
        },
    ]

    report = format_report(test_picks)
    print(report)
    print("\n" + "=" * 50)
    print("To actually send, set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    print("then run: python -c \"from telegram_bot import send_report_sync; "
          "send_report_sync([...])\"")

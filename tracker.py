"""
tracker.py — Performance Tracker for the EGX Intelligence System
=================================================================
Monitors whether past picks hit their Target (+5%) or Stop-Loss (-3%).

HOW IT WORKS:
    1. Fetch all PENDING picks from the database.
    2. For each pick, check today's price data (High & Low).
    3. If High ≥ Target → HIT_TARGET (Win!)
    4. If Low  ≤ Stop   → HIT_STOP  (Loss)
    5. If 5+ trading days old → EXPIRED (no hit either way)
    6. Otherwise → stays PENDING

RUN:
    python tracker.py           ← check outcomes manually
    (Also called automatically by scheduler.py before each analysis)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict

import database
import config

logger = logging.getLogger(__name__)


def check_outcomes() -> Dict:
    """
    Check all PENDING picks against current market data.

    Returns a summary dict:
        {"checked": 5, "hit_target": 1, "hit_stop": 1, "expired": 1, "still_pending": 2}
    """
    database.init_db()
    pending = database.get_pending_picks()

    if not pending:
        logger.info("No pending picks to check.")
        return {"checked": 0, "hit_target": 0, "hit_stop": 0, "expired": 0, "still_pending": 0}

    today = date.today().isoformat()
    summary = {"checked": 0, "hit_target": 0, "hit_stop": 0, "expired": 0, "still_pending": 0}

    for pick in pending:
        summary["checked"] += 1
        pick_id = pick["id"]
        pick_date = pick["date"]
        name = pick["name"]
        target = pick["target_price"]
        stop = pick["stop_loss"]
        entry = pick["entry_price"]

        # Get today's price for this stock.
        prices = database.get_all_prices_for_date(today)
        stock_row = prices[prices["Name"] == name] if not prices.empty else None

        if stock_row is not None and not stock_row.empty:
            row = stock_row.iloc[0]
            high = row.get("High", 0) or 0
            low = row.get("Low", 0) or 0
            last = row.get("Last", 0) or 0

            # Check if target was hit (intraday high reached target).
            if high >= target:
                database.update_pick_outcome(pick_id, "HIT_TARGET", high, today)
                summary["hit_target"] += 1
                logger.info(f"🎯 {name} HIT TARGET! High={high:.2f} ≥ Target={target:.2f}")
                continue

            # Check if stop-loss was hit (intraday low breached stop).
            if low <= stop and low > 0:
                database.update_pick_outcome(pick_id, "HIT_STOP", low, today)
                summary["hit_stop"] += 1
                logger.info(f"🛑 {name} HIT STOP! Low={low:.2f} ≤ Stop={stop:.2f}")
                continue

        # Check if pick has expired (5+ trading days old).
        try:
            pick_dt = datetime.fromisoformat(pick_date).date()
            days_elapsed = (date.today() - pick_dt).days
            # 5 calendar days ≈ 3-4 trading days (conservative)
            if days_elapsed >= 7:
                # Use the last known price as the outcome price.
                last_price = 0
                if stock_row is not None and not stock_row.empty:
                    last_price = stock_row.iloc[0].get("Last", 0) or 0
                database.update_pick_outcome(pick_id, "EXPIRED", last_price, today)
                summary["expired"] += 1
                logger.info(f"⏰ {name} EXPIRED after {days_elapsed} days.")
                continue
        except (ValueError, TypeError):
            pass

        # Still pending.
        summary["still_pending"] += 1

    logger.info(
        f"Tracker Summary: {summary['checked']} checked | "
        f"🎯 {summary['hit_target']} wins | 🛑 {summary['hit_stop']} losses | "
        f"⏰ {summary['expired']} expired | ⏳ {summary['still_pending']} pending"
    )
    return summary


# ─────────────────────────────────────────────────────────────
# CLI: `python tracker.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n📊 Checking pick outcomes...\n")
    result = check_outcomes()
    stats = database.get_performance_stats()

    print(f"\n{'━' * 40}")
    print(f"  Total Picks:  {stats['total']}")
    print(f"  🎯 Wins:      {stats['wins']}")
    print(f"  🛑 Losses:    {stats['losses']}")
    print(f"  ⏰ Expired:   {stats['expired']}")
    print(f"  ⏳ Pending:   {stats['pending']}")
    print(f"  📈 Win Rate:  {stats['win_rate']}%")
    print(f"{'━' * 40}\n")

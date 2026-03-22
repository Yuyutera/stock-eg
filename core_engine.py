"""
core_engine.py — The Unified Pipeline for the EGX Intelligence System
=======================================================================
This is the "main entry point" that ties everything together:

    Scrape  →  Store  →  Analyze  →  Return Picks

The scheduler calls `run()` every morning.
You can also call it manually:  `python core_engine.py`

WHY a separate file?
    Separation of concerns.  The scraper doesn't need to know about
    the database.  The analyzer doesn't need to know about the web.
    This file is the "glue" — the orchestrator.
"""

import logging
from datetime import date, datetime
from typing import Dict, List

import pandas as pd

import config
import database
import scraper
import analyzer

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def is_trading_day() -> bool:
    """
    Check whether today is an EGX trading day (Sun–Thu).

    Python's weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    EGX is open: Sun(6), Mon(0), Tue(1), Wed(2), Thu(3)
    EGX is closed: Fri(4), Sat(5)

    NOTE: This does NOT account for Egyptian public holidays.
    A future enhancement could integrate a holiday calendar API.
    """
    today = datetime.now().weekday()
    is_open = today in config.EGX_TRADING_DAYS
    logger.info(
        f"Today is {'a trading day ✅' if is_open else 'NOT a trading day ❌'} "
        f"(weekday={today})."
    )
    return is_open


def run(force: bool = False) -> Dict:
    """
    Execute the full intelligence pipeline.

    Parameters:
        force — If True, run even on non-trading days (useful for testing).

    Returns:
        A dict with the pipeline results:
        {
            "success": True/False,
            "date": "2026-03-08",
            "stocks_scraped": 30,
            "picks": [ ... ],   # List of Top N pick dicts
            "error": None,      # Error message if something failed
        }
    """
    today = date.today().isoformat()
    result = {
        "success": False,
        "date": today,
        "stocks_scraped": 0,
        "picks": [],
        "error": None,
    }

    try:
        # ── Pre-flight check ──────────────────────────────────
        if not force and not is_trading_day():
            result["error"] = "Market is closed today (Fri/Sat)."
            logger.info(result["error"])
            return result

        # ── Step 1: Initialize database ───────────────────────
        logger.info("━" * 50)
        logger.info("STEP 1: Initializing database…")
        database.init_db()

        # ── Step 2: Scrape EGX data ──────────────────────────
        logger.info("━" * 50)
        logger.info("STEP 2: Scraping EGX equities…")
        df = scraper.scrape_egx()

        if df.empty:
            result["error"] = "Scraper returned no data."
            logger.error(result["error"])
            return result

        result["stocks_scraped"] = len(df)
        logger.info(f"Scraped {len(df)} stocks.")

        # ── Step 3: Save raw data to database ─────────────────
        logger.info("━" * 50)
        logger.info("STEP 3: Saving raw data to database…")
        database.save_daily_prices(df, scrape_date=today)

        # ── Step 4: Enrich with historical data ───────────────
        # For each stock, try to load historical prices from the DB
        # so indicators like SMA(50) actually have enough data points.
        logger.info("━" * 50)
        logger.info("STEP 4: Enriching with historical data…")
        enriched_df = _enrich_with_history(df)

        # ── Step 5: Run the analytical engine ─────────────────
        logger.info("━" * 50)
        logger.info("STEP 5: Running analytical engine…")
        picks = analyzer.find_top_picks(enriched_df)

        # ── Step 6: Save picks ────────────────────────────────
        logger.info("━" * 50)
        logger.info("STEP 6: Saving picks to database…")
        database.save_picks(picks, pick_date=today)

        result["picks"] = picks
        result["success"] = True

        # ── Summary ───────────────────────────────────────────
        logger.info("━" * 50)
        logger.info("✅ Pipeline completed successfully!")
        logger.info(f"   Stocks scraped: {result['stocks_scraped']}")
        logger.info(f"   Picks generated: {len(picks)}")
        for i, p in enumerate(picks, 1):
            logger.info(
                f"   #{i} {p['Name']} | Entry: {p['Entry']} | "
                f"Target: {p['Target']} | Stop: {p['Stop_Loss']} | "
                f"RSI: {p['RSI']} | Spike: {p['Volume_Spike']}×"
            )

    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"Pipeline failed: {e}")

    return result


def _enrich_with_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each stock in today's scrape, look up historical price data
    from the database and concatenate it.  This gives the analyzer
    enough data points for rolling calculations (RSI-14, SMA-50, etc.)

    If no history exists (first time running), we just return the
    original DataFrame — the analyzer handles this gracefully.
    """
    enriched_frames = []

    for stock_name in df["Name"].unique():
        try:
            history = database.get_historical_prices(
                stock_name, days=config.SMA_LONG  # 200 days max
            )

            # Get today's row for this stock.
            today_row = df[df["Name"] == stock_name].copy()

            if not history.empty:
                # Rename to match today's columns before concat.
                history["Name"] = stock_name
                combined = pd.concat(
                    [history, today_row], ignore_index=True
                )
            else:
                combined = today_row

            enriched_frames.append(combined)

        except Exception as e:
            logger.warning(
                f"Could not enrich history for {stock_name}: {e}"
            )
            # Fall back to just today's data.
            enriched_frames.append(df[df["Name"] == stock_name].copy())

    if enriched_frames:
        return pd.concat(enriched_frames, ignore_index=True)
    return df


# ─────────────────────────────────────────────────────────────
# CLI: `python core_engine.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n EGX Intelligence System — Manual Run\n")
    result = run(force=True)  # Force=True to test on any day

    if result["success"]:
        print(f"\n Success! Scraped {result['stocks_scraped']} stocks.")
        print(f"  Generated {len(result['picks'])} picks for {result['date']}.")
    else:
        print(f"\n Pipeline failed: {result['error']}")
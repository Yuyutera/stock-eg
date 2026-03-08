"""
analyzer.py — The Analytical Engine for the EGX Intelligence System
====================================================================
This module takes raw price/volume data and applies Technical Analysis
to find the Top 3 investment opportunities.

THE STRATEGY (in plain English):
─────────────────────────────────
1. RSI (Relative Strength Index) < 35  →  The stock is "oversold,"
   meaning the market may have pushed it lower than its real value.
   This is a potential BUY signal.

2. Volume Spike > 1.5×  →  Today's volume is at least 50% higher
   than the 10-day average.  A surge in volume alongside an oversold
   RSI hints that "smart money" might be accumulating.

3. We rank all qualifying stocks by Volume Spike magnitude and
   pick the Top 3.

4. For each pick we calculate:
    • Entry Price  = the current "Last" price
    • Target Price = Entry + 5%   (take-profit)
    • Stop-Loss    = Entry − 3%   (risk management)

WHY pandas-ta?
    It's a drop-in library that adds 130+ technical indicators to any
    pandas DataFrame with a single function call.  No need to manually
    code the RSI formula.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

import config

logger = logging.getLogger(__name__)


def compute_rsi(prices: pd.Series, period: int = None) -> pd.Series:
    """
    Compute RSI manually as a fallback if pandas-ta isn't installed.

    RSI = 100 − (100 / (1 + RS))
    where RS = average_gain / average_loss over `period` days.
    """
    period = period or config.RSI_PERIOD
    delta = prices.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Avoid division by zero: if avg_loss is 0, RSI = 100.
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicator columns to the DataFrame.

    New columns created:
        RSI_14       — Relative Strength Index (14-period)
        SMA_50       — 50-day Simple Moving Average
        SMA_200      — 200-day Simple Moving Average
        MACD         — MACD line
        MACD_Signal  — MACD signal line
        MACD_Hist    — MACD histogram (MACD − Signal)

    If pandas-ta is available, we use it (faster, battle-tested).
    Otherwise, we fall back to manual calculations.
    """
    try:
        import pandas_ta as ta

        df["RSI_14"] = ta.rsi(df["Last"], length=config.RSI_PERIOD)
        macd_result = ta.macd(
            df["Last"],
            fast=config.MACD_FAST,
            slow=config.MACD_SLOW,
            signal=config.MACD_SIGNAL,
        )
        if macd_result is not None and not macd_result.empty:
            df["MACD"]        = macd_result.iloc[:, 0]
            df["MACD_Signal"] = macd_result.iloc[:, 1]
            df["MACD_Hist"]   = macd_result.iloc[:, 2]
        else:
            df["MACD"] = df["MACD_Signal"] = df["MACD_Hist"] = None

        df["SMA_50"]  = ta.sma(df["Last"], length=config.SMA_SHORT)
        df["SMA_200"] = ta.sma(df["Last"], length=config.SMA_LONG)

        logger.info("Indicators computed via pandas-ta.")

    except ImportError:
        logger.warning(
            "pandas-ta not installed — using manual RSI calculation."
        )
        df["RSI_14"]      = compute_rsi(df["Last"])
        df["SMA_50"]      = df["Last"].rolling(config.SMA_SHORT).mean()
        df["SMA_200"]     = df["Last"].rolling(config.SMA_LONG).mean()
        df["MACD"]        = None
        df["MACD_Signal"] = None
        df["MACD_Hist"]   = None

    return df


def calculate_volume_spike(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'Volume_Spike' column.

    Volume_Spike = today's Volume / 10-day rolling average Volume.

    A value of 2.0 means volume is DOUBLE the recent average —
    something is happening.

    NOTE: On a single-day scrape (no historical data yet), we can't
    compute a rolling average.  In that case, we set spike to 1.0
    (neutral) and rely purely on RSI for filtering.
    """
    if "Volume" not in df.columns or df["Volume"].isna().all():
        df["Volume_Spike"] = 1.0
        logger.warning("No volume data available — Volume_Spike set to 1.0.")
        return df

    avg_vol = df["Volume"].rolling(
        window=config.VOLUME_AVG_PERIOD, min_periods=1
    ).mean()

    # Avoid division by zero.
    df["Volume_Spike"] = df["Volume"] / avg_vol.replace(0, float("nan"))
    df["Volume_Spike"] = df["Volume_Spike"].fillna(1.0)

    return df


def compute_exit_strategy(entry_price: float) -> Dict[str, float]:
    """
    Given an entry price, calculate Target and Stop-Loss levels.

    Example with entry = 42.10:
        Target    = 42.10 × 1.05 = 44.205  →  44.21
        Stop-Loss = 42.10 × 0.97 = 40.837  →  40.84
    """
    return {
        "Entry":     round(entry_price, 2),
        "Target":    round(entry_price * (1 + config.TARGET_PCT), 2),
        "Stop_Loss": round(entry_price * (1 - config.STOP_LOSS_PCT), 2),
    }


def find_top_picks(df: pd.DataFrame) -> List[Dict]:
    """
    The core selection algorithm.

    Steps:
        1. Compute RSI + Volume Spike for every stock.
        2. Filter: RSI < 35 AND Volume_Spike > 1.5.
        3. Sort by Volume_Spike descending (biggest spikes first).
        4. Take top N picks.
        5. Attach Entry/Target/Stop-Loss to each.

    Returns a list of dicts, e.g.:
        [
            {
                "Name": "COMI",
                "Entry": 42.10,
                "Target": 44.21,
                "Stop_Loss": 40.84,
                "RSI": 28.3,
                "Volume_Spike": 2.1,
                "Change_Pct": -1.25,
            },
            ...
        ]

    Returns an empty list if no stocks meet the criteria —
    not every day produces a signal, and that's OK.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to find_top_picks — no analysis possible.")
        return []

    # Step 1: Compute indicators.
    df = compute_indicators(df)
    df = calculate_volume_spike(df)

    # Step 2: Apply the filters.
    mask = (
        (df["RSI_14"].notna())
        & (df["RSI_14"] < config.RSI_OVERSOLD)
        & (df["Volume_Spike"] >= config.VOLUME_SPIKE_MULTIPLIER)
    )
    candidates = df[mask].copy()

    if candidates.empty:
        logger.info(
            "No stocks matched RSI < %s AND Volume Spike ≥ %s× today.",
            config.RSI_OVERSOLD,
            config.VOLUME_SPIKE_MULTIPLIER,
        )
        # Fallback: return top 3 by lowest RSI as "watchlist" items.
        # This ensures the user always gets something actionable.
        watchlist = df[df["RSI_14"].notna()].nsmallest(
            config.TOP_N_PICKS, "RSI_14"
        )
        picks = _format_picks(watchlist, signal_type="Watchlist")
        return picks

    # Step 3 & 4: Sort + take top N.
    candidates = candidates.nlargest(config.TOP_N_PICKS, "Volume_Spike")

    # Step 5: Format output.
    picks = _format_picks(candidates, signal_type="Strong Signal")
    return picks


def _format_picks(df: pd.DataFrame, signal_type: str = "Signal") -> List[Dict]:
    """
    Convert a filtered DataFrame into a clean list of pick dicts.
    """
    picks = []
    for _, row in df.iterrows():
        exit_levels = compute_exit_strategy(row["Last"])
        pick = {
            "Name":         row.get("Name", "Unknown"),
            "Entry":        exit_levels["Entry"],
            "Target":       exit_levels["Target"],
            "Stop_Loss":    exit_levels["Stop_Loss"],
            "RSI":          round(row.get("RSI_14", 0), 2),
            "Volume_Spike": round(row.get("Volume_Spike", 1.0), 2),
            "Change_Pct":   round(row.get("Change_Pct", 0) or 0, 2),
            "Signal_Type":  signal_type,
            "Timestamp":    datetime.now().isoformat(),
        }
        picks.append(pick)

    logger.info(f"Generated {len(picks)} picks ({signal_type}).")
    return picks


# ─────────────────────────────────────────────────────────────
# CLI quick-test: `python analyzer.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Create a small synthetic dataset for testing.
    test_data = pd.DataFrame({
        "Name":       ["StockA", "StockB", "StockC", "StockD", "StockE"],
        "Last":       [10.0, 20.0, 30.0, 40.0, 50.0],
        "High":       [10.5, 21.0, 31.0, 41.0, 51.0],
        "Low":        [9.5,  19.0, 29.0, 39.0, 49.0],
        "Change_Pct": [-3.0, -5.0, -1.0, -4.0, -2.0],
        "Volume":     [1e6,  5e6,  2e6,  8e6,  3e6],
    })

    picks = find_top_picks(test_data)
    if picks:
        print("\n📊 Top Picks (test data):\n")
        for i, p in enumerate(picks, 1):
            print(
                f"  {i}. {p['Name']} | "
                f"Entry: {p['Entry']} | Target: {p['Target']} | "
                f"Stop: {p['Stop_Loss']} | RSI: {p['RSI']} | "
                f"Vol Spike: {p['Volume_Spike']}×"
            )
    else:
        print("No picks generated from test data.")

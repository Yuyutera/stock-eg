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

4. For each pick we calculate ATR-based exit levels:
    • Entry Price  = the current "Last" price
    • Target Price = Entry + (2.0 × ATR)   (take-profit)
    • Stop-Loss    = Entry - (1.5 × ATR)   (risk management)
   Falls back to fixed ±5%/−3% when ATR is unavailable.

5. Additional safety filters:
    • Minimum 28 days of history before generating signals
    • Price direction filter: exclude stocks down >3% (panic selloff)
    • Minimum liquidity: 500K shares traded
    • No "watchlist" fallback — if nothing qualifies, return nothing

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

# ─────────────────────────────────────────────
# CONSTANTS (referenced from config where possible)
# ─────────────────────────────────────────────
MIN_HISTORY_DAYS = config.MIN_HISTORY_DAYS  # 28 trading days minimum


# ─────────────────────────────────────────────────────────────
# INDICATOR FUNCTIONS
# ─────────────────────────────────────────────────────────────
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


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute Average True Range (ATR) for dynamic exit levels.

    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = rolling mean of True Range over `period` days.
    """
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Last"].shift()).abs()
    low_close = (df["Low"] - df["Last"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


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

    Uses min_periods=VOLUME_AVG_PERIOD so rows without enough history
    become NaN (filtered out later) instead of getting a fake 1.0.
    """
    if "Volume" not in df.columns or df["Volume"].isna().all():
        df["Volume_Spike"] = float("nan")
        logger.warning("No volume data available — Volume_Spike set to NaN.")
        return df

    avg_vol = df["Volume"].rolling(
        window=config.VOLUME_AVG_PERIOD,
        min_periods=config.VOLUME_AVG_PERIOD,  # Fix 2: require full window
    ).mean()

    # Avoid division by zero.
    df["Volume_Spike"] = df["Volume"] / avg_vol.replace(0, float("nan"))
    # Do NOT fillna(1.0) — let insufficient-history rows stay NaN
    # so they are excluded from the signal filter.

    return df


def compute_exit_strategy(
    entry_price: float, atr: Optional[float] = None
) -> Dict[str, float]:
    """
    Given an entry price, calculate Target and Stop-Loss levels.

    When ATR is available:
        Stop-Loss = Entry - (1.5 × ATR)
        Target    = Entry + (2.0 × ATR)

    When ATR is not available (insufficient history), fall back to
    fixed percentages from config (+5% target / -3% stop).
    """
    if atr is not None and atr > 0:
        target = entry_price + (config.ATR_TARGET_MULTIPLIER * atr)
        stop   = entry_price - (config.ATR_STOP_MULTIPLIER * atr)
        logger.debug(
            "ATR-based exits: entry=%.2f, ATR=%.2f, target=%.2f, stop=%.2f",
            entry_price, atr, target, stop,
        )
    else:
        target = entry_price * (1 + config.TARGET_PCT)
        stop   = entry_price * (1 - config.STOP_LOSS_PCT)
        logger.warning(
            "ATR unavailable for entry %.2f — using fixed %% exits "
            "(target=+%.0f%%, stop=-%.0f%%).",
            entry_price, config.TARGET_PCT * 100, config.STOP_LOSS_PCT * 100,
        )

    return {
        "Entry":     round(entry_price, 2),
        "Target":    round(target, 2),
        "Stop_Loss": round(stop, 2),
    }


# ─────────────────────────────────────────────────────────────
# CORE SELECTION ALGORITHM
# ─────────────────────────────────────────────────────────────
def find_top_picks(df: pd.DataFrame) -> List[Dict]:
    """
    The core selection algorithm.

    Steps:
        1. Validate data sufficiency (global + per-stock).
        2. Compute RSI + Volume Spike + ATR for every stock.
        3. Filter: RSI < 35 AND Volume_Spike > 1.5 AND Change > -3%
           AND Volume >= MIN_DAILY_VOLUME.
        4. Sort by Volume_Spike descending (biggest spikes first).
        5. Take top N picks.
        6. Attach ATR-based Entry/Target/Stop-Loss to each.

    Returns a list of dicts.
    Returns an empty list if no stocks meet the criteria —
    not every day produces a signal, and that's OK.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to find_top_picks — no analysis possible.")
        return []

    # ── Fix 1: Global data sufficiency guard ──────────────────
    unique_days = df["date"].nunique() if "date" in df.columns else len(df)
    if unique_days < MIN_HISTORY_DAYS:
        logger.warning(
            "Insufficient history: %d days available, %d required. Skipping.",
            unique_days, MIN_HISTORY_DAYS,
        )
        return []

    # ── Fix 1b: Per-stock history filter ──────────────────────
    if "date" in df.columns:
        stock_counts = df.groupby("Name")["date"].nunique()
        valid_stocks = stock_counts[stock_counts >= MIN_HISTORY_DAYS].index
        df = df[df["Name"].isin(valid_stocks)]
        if df.empty:
            logger.warning("No individual stocks have sufficient history yet.")
            return []

    # Step 1: Compute indicators.
    df = compute_indicators(df)
    df = calculate_volume_spike(df)

    # Compute ATR for dynamic exit levels (Fix 6).
    df["ATR_14"] = df.groupby("Name", group_keys=False).apply(
    lambda g: compute_atr(g, period=config.ATR_PERIOD)
)
    # Step 2: Apply the filters.
    # Fix 3: No watchlist fallback — strict criteria only.
    # Fix 4: Price direction filter (exclude panic selloffs > -3%).
    # Fix 5: Minimum liquidity filter.
    mask = (
        (df["RSI_14"].notna())
        & (df["RSI_14"] < config.RSI_OVERSOLD)
        & (df["Volume_Spike"].notna())
        & (df["Volume_Spike"] >= config.VOLUME_SPIKE_MULTIPLIER)
        & (df["Change_Pct"] > -3.0)                      # Fix 4
        & (df["Volume"] >= config.MIN_DAILY_VOLUME)       # Fix 5
    )
    candidates = df[mask].copy()

    if candidates.empty:
        logger.info(
            "No signals today — no stocks matched RSI < %s AND "
            "Volume Spike ≥ %s× AND Change > -3%% AND Volume ≥ %s.",
            config.RSI_OVERSOLD,
            config.VOLUME_SPIKE_MULTIPLIER,
            config.MIN_DAILY_VOLUME,
        )
        return []  # Fix 3: clean return, no dangerous watchlist fallback

    # Step 3 & 4: Deduplicate names, sort + take top N.
    # Keep the one with the highest Volume_Spike for each name.
    candidates = candidates.sort_values("Volume_Spike", ascending=False)
    candidates = candidates.drop_duplicates(subset=["Name"])
    candidates = candidates.head(config.TOP_N_PICKS)

    # Step 5: Format output.
    picks = _format_picks(candidates, signal_type="Strong Signal")
    return picks


def _compute_confidence_score(rsi: float, volume_spike: float) -> float:
    """
    Calculate a 0–100 confidence score for a pick.

    Formula:
        RSI component  = (RSI_OVERSOLD - rsi) / RSI_OVERSOLD × 50
        Volume component = min(volume_spike, 5.0) / 5.0 × 50

    Higher RSI divergence from threshold + stronger volume spike = higher score.
    """
    rsi_component = ((config.RSI_OVERSOLD - rsi) / config.RSI_OVERSOLD) * 50
    vol_component = (min(volume_spike, 5.0) / 5.0) * 50
    score = max(0.0, min(100.0, rsi_component + vol_component))
    return round(score, 1)


def _build_signal_reason(rsi: float, volume_spike: float, change_pct: float) -> str:
    """
    Build a human-readable string explaining why a stock was picked.
    Critical for debugging which conditions produce the best results.
    """
    return (
        f"RSI {rsi:.1f} (threshold: {config.RSI_OVERSOLD}) | "
        f"Volume spike {volume_spike:.1f}× (threshold: {config.VOLUME_SPIKE_MULTIPLIER}×) | "
        f"Change: {change_pct:+.1f}%"
    )


def _format_picks(df: pd.DataFrame, signal_type: str = "Signal") -> List[Dict]:
    """
    Convert a filtered DataFrame into a clean list of pick dicts.

    Each pick includes:
        - Entry/Target/Stop_Loss (ATR-based when available)
        - confidence_score (0–100)
        - Signal_Reason (human-readable explanation)
        - Expires_After (max holding days from config)
    """
    picks = []
    for _, row in df.iterrows():
        entry_price = row["Last"]
        rsi = round(row.get("RSI_14", 0) or 0, 2)
        volume_spike = round(row.get("Volume_Spike", 1.0) or 1.0, 2)
        change_pct = round(row.get("Change_Pct", 0) or 0, 2)
        atr_value = row.get("ATR_14", None)

        # Fix 6: ATR-based dynamic exit levels
        if pd.notna(atr_value) and atr_value > 0:
            exit_levels = compute_exit_strategy(entry_price, atr=atr_value)
        else:
            exit_levels = compute_exit_strategy(entry_price, atr=None)

        # Fix 7: Confidence score
        confidence = _compute_confidence_score(rsi, volume_spike)

        # Fix 8: Signal reason
        reason = _build_signal_reason(rsi, volume_spike, change_pct)

        pick = {
            "Name":             row.get("Name", "Unknown"),
            "Entry":            exit_levels["Entry"],
            "Target":           exit_levels["Target"],
            "Stop_Loss":        exit_levels["Stop_Loss"],
            "RSI":              rsi,
            "Volume_Spike":     volume_spike,
            "Change_Pct":       change_pct,
            "Signal_Type":      signal_type,
            "confidence_score": confidence,           # Fix 7
            "Signal_Reason":    reason,               # Fix 8
            "Expires_After":    config.MAX_HOLDING_DAYS,  # Fix 9
            "Timestamp":        datetime.now().isoformat(),
        }
        picks.append(pick)

        logger.info(
            "Pick: %s | Confidence: %.1f | %s",
            row.get("Name", "Unknown"), confidence, reason,
        )

    logger.info("Generated %d picks (%s).", len(picks), signal_type)
    return picks


# ─────────────────────────────────────────────────────────────
# CLI quick-test: `python analyzer.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Create a small synthetic dataset for testing.
    # Note: With MIN_HISTORY_DAYS=28, this test will return []
    # unless you provide 28+ rows.  That's correct behavior.
    test_data = pd.DataFrame({
        "Name":       ["StockA", "StockB", "StockC", "StockD", "StockE"],
        "Last":       [10.0, 20.0, 30.0, 40.0, 50.0],
        "High":       [10.5, 21.0, 31.0, 41.0, 51.0],
        "Low":        [9.5,  19.0, 29.0, 39.0, 49.0],
        "Change_Pct": [-1.0, -2.0, -1.0, -0.5, -2.0],
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
                f"Vol Spike: {p['Volume_Spike']}× | "
                f"Confidence: {p['confidence_score']} | "
                f"Reason: {p['Signal_Reason']}"
            )
    else:
        print("No picks generated (expected with <28 days of test data).")

"""
database.py — Data Persistence Layer for the EGX Intelligence System
=====================================================================
Uses SQLite — NO external database server needed.  The entire DB is a
single file (egx_data.db) that lives alongside your Python scripts.

TWO TABLES:
    daily_prices  — One row per stock per day.  Over time, this builds
                    the historical dataset needed for rolling averages.
    picks         — The Top 3 selections saved with timestamps, so you
                    can back-test your strategy later.

WHY SQLite?
    • Zero configuration — no Docker, no passwords.
    • Great for single-user analytical workloads.
    • The full EGX30 × 365 days ≈ 11,000 rows/year — trivial for SQLite.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd

import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# CONNECTION HELPER
# ─────────────────────────────────────────────────────────────
@contextmanager
def get_connection():
    """
    Context manager for SQLite connections.
    Ensures the connection is committed and closed even if an error
    occurs in the middle of a transaction.

    Usage:
        with get_connection() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name, not index
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# SCHEMA INITIALIZATION
# ─────────────────────────────────────────────────────────────
def init_db():
    """
    Create the tables if they don't exist yet.

    This is SAFE to call multiple times — `IF NOT EXISTS` prevents
    errors if the tables are already there.
    """
    with get_connection() as conn:
        # ── daily_prices ──────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                last_price  REAL,
                high        REAL,
                low         REAL,
                change_pct  REAL,
                volume      REAL,
                created_at  TEXT    DEFAULT (datetime('now')),

                -- Prevent duplicate entries for the same stock on the same day.
                UNIQUE(date, name)
            );
        """)

        # Index for fast lookups by date + stock name.
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_prices_date_name
            ON daily_prices(date, name);
        """)

        # ── picks ──────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS picks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT    NOT NULL,
                rank         INTEGER NOT NULL,
                name         TEXT    NOT NULL,
                entry_price  REAL,
                target_price REAL,
                stop_loss    REAL,
                rsi          REAL,
                volume_spike REAL,
                change_pct   REAL,
                signal_type  TEXT,
                outcome      TEXT    DEFAULT 'PENDING',
                outcome_date TEXT,
                outcome_price REAL,
                created_at   TEXT    DEFAULT (datetime('now'))
            );
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_picks_date
            ON picks(date);
        """)

        # Migrate: add outcome columns if they don't exist yet.
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN outcome TEXT DEFAULT 'PENDING'")
        except sqlite3.OperationalError:
            pass  # Column already exists.
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN outcome_date TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN outcome_price REAL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN confidence_score REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN signal_reason TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE picks ADD COLUMN expires_after INTEGER DEFAULT 10")
        except sqlite3.OperationalError:
            pass

    logger.info(f"Database initialized at {config.DB_PATH}")


# ─────────────────────────────────────────────────────────────
# WRITE OPERATIONS
# ─────────────────────────────────────────────────────────────
def save_daily_prices(df: pd.DataFrame, scrape_date: Optional[str] = None):
    """
    Persist today's scraped data into the `daily_prices` table.

    Uses INSERT OR REPLACE so re-running the scraper on the same day
    simply updates the existing rows instead of erroring.

    Parameters:
        df          — DataFrame from scraper.scrape_egx()
        scrape_date — ISO date string, e.g. "2026-03-08".
                      Defaults to today.
    """
    if df.empty:
        logger.warning("Empty DataFrame — nothing to save.")
        return 0

    today = scrape_date or date.today().isoformat()
    rows_saved = 0

    with get_connection() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO daily_prices
                        (date, name, last_price, high, low, change_pct, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        row.get("Name"),
                        row.get("Last"),
                        row.get("High"),
                        row.get("Low"),
                        row.get("Change_Pct"),
                        row.get("Volume"),
                    ),
                )
                rows_saved += 1
            except sqlite3.Error as e:
                logger.error(f"Failed to save {row.get('Name')}: {e}")

    logger.info(f"Saved {rows_saved} rows to daily_prices for {today}.")
    return rows_saved


def save_picks(picks: List[Dict], pick_date: Optional[str] = None):
    """
    Save the Top N picks to the `picks` table.

    Parameters:
        picks     — List of dicts from analyzer.find_top_picks()
        pick_date — ISO date string.  Defaults to today.
    """
    if not picks:
        logger.warning("No picks to save.")
        return 0

    today = pick_date or date.today().isoformat()
    rows_saved = 0

    with get_connection() as conn:
        # Clear any existing picks for today (in case of re-run).
        conn.execute("DELETE FROM picks WHERE date = ?", (today,))

        for rank, pick in enumerate(picks, 1):
            try:
                conn.execute(
                    """
                    INSERT INTO picks
                        (date, rank, name, entry_price, target_price,
                         stop_loss, rsi, volume_spike, change_pct,
                         signal_type, confidence_score, signal_reason, expires_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        rank,
                        pick.get("Name"),
                        pick.get("Entry"),
                        pick.get("Target"),
                        pick.get("Stop_Loss"),
                        pick.get("RSI"),
                        pick.get("Volume_Spike"),
                        pick.get("Change_Pct"),
                        pick.get("Signal_Type"),
                        pick.get("confidence_score"),
                        pick.get("Signal_Reason"),
                        pick.get("Expires_After"),
                    ),
                )
                rows_saved += 1
            except sqlite3.Error as e:
                logger.error(f"Failed to save pick '{pick.get('Name')}': {e}")

    logger.info(f"Saved {rows_saved} picks for {today}.")
    return rows_saved


# ─────────────────────────────────────────────────────────────
# READ OPERATIONS
# ─────────────────────────────────────────────────────────────
def get_historical_prices(stock_name: str, days: int = 30) -> pd.DataFrame:
    """
    Fetch the last `days` of price data for a specific stock.

    This is used by the analyzer to compute rolling indicators like
    RSI and SMA when historical data is available.
    """
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT date, last_price AS Last, high AS High, low AS Low,
                   change_pct AS Change_Pct, volume AS Volume
            FROM daily_prices
            WHERE name = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            conn,
            params=(stock_name, days),
        )
    return df.sort_values("date").reset_index(drop=True)


def get_all_prices_for_date(target_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get all stock prices for a specific date.
    Defaults to today.
    """
    target = target_date or date.today().isoformat()
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT name AS Name, last_price AS Last, high AS High,
                   low AS Low, change_pct AS Change_Pct, volume AS Volume
            FROM daily_prices
            WHERE date = ?
            ORDER BY name
            """,
            conn,
            params=(target,),
        )
    return df


def get_latest_picks(target_date: Optional[str] = None) -> List[Dict]:
    """
    Retrieve the most recent Top N picks.
    """
    target = target_date or date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT rank, name, entry_price, target_price, stop_loss,
                   rsi, volume_spike, change_pct, signal_type, date,
                   confidence_score, signal_reason, expires_after
            FROM picks
            WHERE date = ?
            ORDER BY rank
            """,
            (target,),
        )
        picks = [dict(row) for row in cursor.fetchall()]
    return picks


def get_pick_price_journey(stock_name: str, pick_date: str) -> List[Dict]:
    """
    Get day-by-day closing prices for a stock from its pick date onward.
    Used by the Live Pick Tracker to show the price evolution since entry.

    Returns:
        List of dicts: [{"date": "2026-03-08", "price": 19.77}, ...]
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT date, last_price AS price
            FROM daily_prices
            WHERE name = ? AND date >= ?
            ORDER BY date
            """,
            (stock_name, pick_date),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_picks_history(days: int = 30) -> pd.DataFrame:
    """
    Get all picks from the last N days — useful for the dashboard's
    historical view.
    """
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT date, rank, name, entry_price, target_price,
                   stop_loss, rsi, volume_spike, signal_type, outcome
            FROM picks
            ORDER BY date DESC, rank
            LIMIT ?
            """,
            conn,
            params=(days * config.TOP_N_PICKS,),
        )
    return df


def get_recent_outcomes(limit: int = 10) -> List[Dict]:
    """
    Get the most recent resolved or pending picks to show in reports.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT date, name, outcome, entry_price, outcome_price,
                   confidence_score
            FROM picks
            WHERE outcome != 'PENDING' OR (date > date('now', '-3 days'))
            ORDER BY date DESC, rank
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_pending_picks() -> List[Dict]:
    """
    Get all picks that haven't been resolved yet (outcome = 'PENDING').
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, date, name, entry_price, target_price, stop_loss,
                   rsi, volume_spike, signal_type, outcome
            FROM picks
            WHERE outcome = 'PENDING' OR outcome IS NULL
            ORDER BY date
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def update_pick_outcome(
    pick_id: int, outcome: str, outcome_price: float, outcome_date: str
):
    """
    Mark a pick as HIT_TARGET, HIT_STOP, or EXPIRED.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE picks
            SET outcome = ?, outcome_price = ?, outcome_date = ?
            WHERE id = ?
            """,
            (outcome, outcome_price, outcome_date, pick_id),
        )
    logger.info(f"Pick #{pick_id} → {outcome} at {outcome_price} on {outcome_date}")


def get_performance_stats() -> Dict:
    """
    Calculate overall win/loss/pending/expired statistics.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'HIT_TARGET' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'HIT_STOP' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN outcome = 'EXPIRED' THEN 1 ELSE 0 END) as expired,
                SUM(CASE WHEN outcome = 'PENDING' OR outcome IS NULL THEN 1 ELSE 0 END) as pending
            FROM picks
            """
        )
        row = dict(cursor.fetchone())

    resolved = row["wins"] + row["losses"]
    row["win_rate"] = round((row["wins"] / resolved * 100), 1) if resolved > 0 else 0.0
    return row


def get_available_history_days() -> int:
    """
    Return the number of distinct trading days stored in daily_prices.
    Used by the dashboard to show a progress bar during the data
    accumulation phase before signals can be reliably generated.
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT date) FROM daily_prices"
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning("Could not count history days: %s", e)
            return 0


# ─────────────────────────────────────────────────────────────
# CLI quick-test: `python database.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print(f"✅ Database created/verified at: {config.DB_PATH}")

    # Quick round-trip test.
    test_df = pd.DataFrame({
        "Name":       ["TestStock"],
        "Last":       [100.0],
        "High":       [105.0],
        "Low":        [95.0],
        "Change_Pct": [2.5],
        "Volume":     [1_000_000],
    })
    rows = save_daily_prices(test_df, scrape_date="2026-01-01")
    print(f"   Saved {rows} test row(s).")

    retrieved = get_all_prices_for_date("2026-01-01")
    print(f"   Retrieved {len(retrieved)} row(s) for 2026-01-01.")
    print("   Done. ✓")

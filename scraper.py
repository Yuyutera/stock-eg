"""
scraper.py — Resilient Data Acquisition for the EGX Intelligence System
========================================================================
WHY cloudscraper?
    Investing.com uses Cloudflare protection. The standard `requests`
    library will get a 403 Forbidden.  `cloudscraper` solves the
    JavaScript challenge automatically — no Selenium needed.

WHY BeautifulSoup?
    It's the most forgiving HTML parser. Even if Investing.com ships
    slightly malformed HTML, BS4 can still navigate it.

FLOW:
    1. Hit the equities page with cloudscraper.
    2. Find the data table.
    3. Parse each row into a dict.
    4. Clean strings → floats (handling "1.2M", "500K", etc.).
    5. Return a pandas DataFrame ready for analysis.
"""

import logging
import re
import time
from typing import Optional

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup

import config

# Set up a logger so we can trace issues without print-debugging.
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


# ─────────────────────────────────────────────────────────────
# HELPER: Convert volume/price strings to numeric floats
# ─────────────────────────────────────────────────────────────
def clean_numeric(value: str) -> Optional[float]:
    """
    Convert a display string into a Python float.

    Examples:
        "15.50"   → 15.50
        "1.2M"    → 1_200_000.0
        "500K"    → 500_000.0
        "1.5B"    → 1_500_000_000.0
        "-2.30%"  → -2.30
        "N/A"     → None
        ""        → None

    WHY this is crucial:
        Investing.com shows volumes like "1.2M". If we don't convert
        them, our Volume Spike calculation will compare strings — which
        is meaningless.
    """
    if not value or value.strip() in ("N/A", "-", "—", ""):
        return None

    # Remove commas, whitespace, and percentage signs.
    text = value.strip().replace(",", "").replace("%", "")

    # Multiplier suffixes used on Investing.com.
    multipliers = {
        "B": 1_000_000_000,   # Billions
        "M": 1_000_000,       # Millions
        "K": 1_000,           # Thousands
    }

    try:
        suffix = text[-1].upper()
        if suffix in multipliers:
            return float(text[:-1]) * multipliers[suffix]
        return float(text)
    except (ValueError, IndexError):
        logger.warning(f"Could not parse numeric value: '{value}'")
        return None


def clean_change_pct(value: str) -> Optional[float]:
    """
    Parse a percentage-change string like "+1.25%" or "−0.40%".
    Handles both ASCII minus (-) and Unicode minus (−).
    """
    if not value or value.strip() in ("N/A", "-", "—", ""):
        return None
    text = value.strip().replace(",", "").replace("%", "")
    # Replace Unicode minus with ASCII minus for float().
    text = text.replace("−", "-").replace("\u2212", "-")
    try:
        return float(text)
    except ValueError:
        logger.warning(f"Could not parse change%: '{value}'")
        return None


# ─────────────────────────────────────────────────────────────
# CORE: Scrape the EGX equities table
# ─────────────────────────────────────────────────────────────
def scrape_egx() -> pd.DataFrame:
    """
    Scrape the Egyptian Stock Exchange equities page and return a
    cleaned DataFrame with columns:

        Name | Last | High | Low | Change_Pct | Volume

    Implements retry logic: up to MAX_RETRIES attempts with
    exponential back-off (2s → 4s → 8s …).

    Returns an EMPTY DataFrame if all retries fail (the caller
    decides what to do — log it, alert the user, etc.).
    """
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )

    last_error: Optional[Exception] = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.info(
                f"Scraping EGX equities (attempt {attempt}/{config.MAX_RETRIES})…"
            )

            response = scraper.get(
                config.SCRAPE_URL,
                headers=config.REQUEST_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()  # Raises on 4xx / 5xx

            # ── Parse the HTML ──────────────────────────────
            soup = BeautifulSoup(response.text, "html.parser")

            # Investing.com wraps equities data in a <table>.
            # We look for common table identifiers.
            table = (
                soup.find("table", {"id": "cr1"})              # legacy ID
                or soup.find("table", class_=re.compile(r"genTbl|datatable", re.I))
                or soup.find("table")                            # last resort
            )

            if table is None:
                raise ValueError(
                    "Could not locate the equities table in the HTML. "
                    "The page layout may have changed."
                )

            # ── Extract rows ─────────────────────────────────
            rows_data = []
            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 8:
                    continue  # Skip rows with insufficient columns

                # Extract raw text from each cell.
                raw = [cell.get_text(strip=True) for cell in cells]

                # Updated column order on Investing.com EGX page (verified 2026-03-08):
                #   0: Checkbox/Icon
                #   1: Name
                #   2: Last
                #   3: High
                #   4: Low
                #   5: Chg. (absolute)
                #   6: Change%
                #   7: Volume
                stock = {
                    "Name":       raw[1],
                    "Last":       clean_numeric(raw[2]),
                    "High":       clean_numeric(raw[3]),
                    "Low":        clean_numeric(raw[4]),
                    "Change_Pct": clean_change_pct(raw[6]),
                    "Volume":     clean_numeric(raw[7]),
                }

                # Only include rows where we successfully parsed the price.
                if stock["Last"] is not None:
                    rows_data.append(stock)

            if not rows_data:
                raise ValueError(
                    "Table found but no valid rows could be parsed. "
                    "Column layout may have changed."
                )

            df = pd.DataFrame(rows_data)
            logger.info(f"Successfully scraped {len(df)} stocks from EGX.")
            return df

        except Exception as e:
            last_error = e
            wait = 2 ** attempt  # Exponential back-off: 2, 4, 8 …
            logger.error(
                f"Attempt {attempt} failed: {e}. "
                f"Retrying in {wait}s…"
            )
            time.sleep(wait)

    # All retries exhausted — return empty DataFrame so the system
    # doesn't crash.  The caller can check `df.empty`.
    logger.critical(
        f"All {config.MAX_RETRIES} scraping attempts failed. "
        f"Last error: {last_error}"
    )
    return pd.DataFrame(columns=["Name", "Last", "High", "Low", "Change_Pct", "Volume"])


# ─────────────────────────────────────────────────────────────
# CLI quick-test: `python scraper.py`
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = scrape_egx()
    if df.empty:
        print("⚠  Scraper returned no data. Check logs above.")
    else:
        print(f"\n✅ Scraped {len(df)} EGX stocks:\n")
        print(df.to_string(index=False))
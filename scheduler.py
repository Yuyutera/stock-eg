"""
scheduler.py — Daily Orchestration for the EGX Intelligence System
===================================================================
Runs the full pipeline every morning at 08:30 CLT (Cairo Local Time),
then sends the Telegram report automatically.

IMPORTANT: EGX Calendar Awareness
    The Egyptian Stock Exchange is open Sunday → Thursday.
    Friday and Saturday are the weekend.
    This scheduler ONLY fires on EGX trading days.

RUN:
    python scheduler.py       ← starts the scheduler (keep it running)
    python scheduler.py --now ← run once immediately for testing

WHY APScheduler?
    Lightweight, pure-Python job scheduler with cron-like syntax.
    No external services (no crontab, no Task Scheduler, no celery).
    Works on Windows, Linux, and macOS.
"""

import argparse
import logging
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import core_engine
import telegram_bot

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def morning_job():
    """
    The main daily job. Called by APScheduler at 08:30 CLT.

    Steps:
        1. Run the core pipeline (scrape + analyze).
        2. If successful, send the Telegram report.
        3. Log the outcome.
    """
    logger.info("=" * 60)
    logger.info("🌅 MORNING JOB TRIGGERED — %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # Run the pipeline.
    result = core_engine.run(force=False)

    if result["success"]:
        picks = result["picks"]
        logger.info(f"Pipeline returned {len(picks)} picks.")

        # Send the Telegram report.
        try:
            sent = telegram_bot.send_report_sync(picks, result["date"])
            if sent:
                logger.info("📨 Telegram report sent successfully.")
            else:
                logger.warning("⚠ Telegram send returned False. Check credentials.")
        except Exception as e:
            logger.error(f"Failed to send Telegram report: {e}")

    elif result["error"] == "Market is closed today (Fri/Sat).":
        logger.info("Market closed — no action needed. 😴")

    else:
        logger.error(f"Pipeline failed: {result['error']}")

        # Optionally, send an error notification to Telegram.
        try:
            error_msg = (
                f"⚠️ *EGX Pipeline Error*\n\n"
                f"Date: {result['date']}\n"
                f"Error: `{result['error']}`\n\n"
                f"_Please check the logs._"
            )
            telegram_bot.send_report_sync([], result["date"])
        except Exception:
            pass  # Don't let the error notification crash the scheduler.

    logger.info("=" * 60)
    logger.info("Morning job completed.\n")


def start_scheduler():
    """
    Start the APScheduler with a cron trigger for EGX trading days.

    Schedule: 08:30 CLT, Sunday through Thursday.
        - day_of_week: 'sun,mon,tue,wed,thu'
        - hour: 8, minute: 30
        - timezone: Africa/Cairo
    """
    scheduler = BlockingScheduler()

    # APScheduler uses 3-letter day abbreviations.
    # EGX trading days: Sun, Mon, Tue, Wed, Thu.
    trigger = CronTrigger(
        day_of_week="sun,mon,tue,wed,thu",
        hour=config.SCHEDULE_HOUR,
        minute=config.SCHEDULE_MINUTE,
        timezone=config.SCHEDULE_TIMEZONE,
    )

    scheduler.add_job(
        morning_job,
        trigger=trigger,
        id="egx_morning_report",
        name="EGX Morning Report",
        misfire_grace_time=3600,  # If the job misses, still run within 1 hour.
        max_instances=1,          # Never run 2 instances simultaneously.
    )

    logger.info("━" * 50)
    logger.info("📅 EGX Scheduler Started")
    logger.info(f"   Schedule: {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d} CLT")
    logger.info("   Days: Sun, Mon, Tue, Wed, Thu")
    logger.info(f"   Timezone: {config.SCHEDULE_TIMEZONE}")
    logger.info("━" * 50)
    logger.info("Waiting for next trigger… (Ctrl+C to stop)\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
        scheduler.shutdown(wait=False)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EGX Intelligence System — Scheduler"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the morning job immediately (for testing), then exit.",
    )
    args = parser.parse_args()

    if args.now:
        print("\n🚀 Running morning job NOW (test mode)…\n")
        morning_job()
        print("\n✅ Done. Exiting.\n")
    else:
        start_scheduler()

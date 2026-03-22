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
import tracker

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def morning_job():
    """
    The main analysis job. Called by APScheduler at each scheduled time.

    Steps:
        1. Check outcomes of previous picks (tracker).
        2. Run the core pipeline (scrape + analyze).
        3. If successful, send the Telegram report.
        4. Log the outcome.
    """
    logger.info("=" * 60)
    logger.info("📊 ANALYSIS JOB TRIGGERED — %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # Step 0: Check outcomes of previous picks.
    try:
        tracker_result = tracker.check_outcomes()
        logger.info(f"Tracker: {tracker_result}")
    except Exception as e:
        logger.error(f"Tracker error (non-fatal): {e}")

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
    logger.info("Analysis job completed.\n")


def start_scheduler():
    """
    Start the APScheduler with 3 cron triggers for EGX trading days.

    Schedule (Cairo Time, Sun–Thu):
        1. 10:00 AM  — Market Open
        2. 12:15 PM  — Mid-Day
        3.  2:00 PM  — Pre-Close (30 min before 2:30 PM close)
    """
    scheduler = BlockingScheduler()

    # Register a cron job for each scheduled time.
    for i, schedule in enumerate(config.SCHEDULE_TIMES):
        trigger = CronTrigger(
            day_of_week="sun,mon,tue,wed,thu",
            hour=schedule["hour"],
            minute=schedule["minute"],
            timezone=config.SCHEDULE_TIMEZONE,
        )

        scheduler.add_job(
            morning_job,
            trigger=trigger,
            id=f"egx_report_{i}",
            name=f"EGX {schedule['label']} Report",
            misfire_grace_time=3600,
            max_instances=1,
        )

    logger.info("━" * 50)
    logger.info("📅 EGX Scheduler Started — 3 Daily Runs")
    for s in config.SCHEDULE_TIMES:
        logger.info(f"   ⏰ {s['hour']:02d}:{s['minute']:02d} CLT — {s['label']}")
    logger.info(f"   Days: Sun, Mon, Tue, Wed, Thu")
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

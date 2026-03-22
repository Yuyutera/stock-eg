@echo off
cd C:\stock
set PYTHONIOENCODING=utf-8
python core_engine.py > C:\stock\logs\egx_log.txt 2>&1
python -c "from telegram_bot import send_report_sync; send_report_sync([])" >> C:\stock\logs\egx_log.txt 2>&1
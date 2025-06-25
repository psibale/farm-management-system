# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from drive_backup import backup_files_to_drive
import logging

def scheduled_backup():
    try:
        backup_files_to_drive()
        print("✅ Automated backup completed successfully.")
    except Exception as e:
        logging.error(f"❌ Backup failed: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_backup, trigger="interval", hours=24)  # 🔁 Runs every 24 hours
    scheduler.start()

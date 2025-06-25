# modules/backup.py
from flask import Blueprint, redirect, url_for, flash
from drive_backup import backup_files_to_drive
from modules.utils import role_required

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

@backup_bp.route("/now")
@role_required(['Admin'])
def backup_now():
    try:
        backup_files_to_drive()
        flash("✅ Backup to Google Drive completed successfully.", "success")
    except Exception as e:
        flash(f"❌ Backup failed: {str(e)}", "danger")
    return redirect(url_for("inventory.dashboard"))

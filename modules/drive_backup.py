# drive_backup.py

import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def backup_files_to_drive():
    # Authorize
    gauth = GoogleAuth()

    # Try to load saved credentials, else authenticate
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize if everything is fine
        gauth.Authorize()

    # Save credentials for future use
    gauth.SaveCredentialsFile("mycreds.txt")

    drive = GoogleDrive(gauth)

    # List of files to backup
    files_to_backup = [
        "inventory_data.xlsx",
        "inventory_logs.xlsx",
        "inventory_requests.xlsx",
        "weather_data.xlsx",
        "irrigation_records.xlsx",
        "attendance.xlsx",
        "crop_estimates.xlsx",
        "employees.xlsx",
        "equipment_maintenance.xlsx",
        "equipment_records.xlsx",
        "fertilizer_records.xlsx",
        "field_polygons.xlsx",
        "grade_rules.xlsx",
        "harvesting_records.xlsx",
        "herbicide_records.xlsx",
        "leave_records.xlsx",
        "pest_disease_control.xlsx",
        "planting_records.xlsx",
        "registered_fields.xlsx",
        "season_data.xlsx",
        "tractor_operations.xlsx",
        "weeding_records.xlsx",
        "yield_data.xlsx"
    ]

    for file in files_to_backup:
        if os.path.exists(f"data/{file}"):  # assumes your data lives in a "data/" directory
            f_drive = drive.CreateFile({'title': file})
            f_drive.SetContentFile(f"data/{file}")
            f_drive.Upload()
            print(f"✅ Uploaded: {file}")
        else:
            print(f"⚠️ File not found: {file}")

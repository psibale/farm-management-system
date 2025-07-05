# sync_manager.py

import os
import time
from modules.gdrive_sync import upload_excel_to_drive

# Files to monitor and sync (relative or absolute paths)
WATCHED_FILES = [
    'data/yield_data.xlsx',
    'data/harvest_program.xlsx',
    'data/ers_reports.xlsx',
    'ERS_reports'  # You can include folders too
]

# Stores last modified timestamps
last_modified = {}

def initialize_timestamps():
    for path in WATCHED_FILES:
        if os.path.exists(path):
            if os.path.isfile(path):
                last_modified[path] = os.path.getmtime(path)
            elif os.path.isdir(path):
                last_modified[path] = get_latest_folder_timestamp(path)

def get_latest_folder_timestamp(folder):
    latest = 0
    for root, _, files in os.walk(folder):
        for file in files:
            filepath = os.path.join(root, file)
            mtime = os.path.getmtime(filepath)
            if mtime > latest:
                latest = mtime
    return latest

def sync_if_modified():
    for path in WATCHED_FILES:
        if not os.path.exists(path):
            continue

        if os.path.isfile(path):
            current_mtime = os.path.getmtime(path)
        else:
            current_mtime = get_latest_folder_timestamp(path)

        if last_modified.get(path) != current_mtime:
            print(f"[SYNC] Detected change in {path}, uploading to Google Drive...")
            upload_excel_to_drive(path)
            last_modified[path] = current_mtime

# You can call this from routes or on a schedule
initialize_timestamps()

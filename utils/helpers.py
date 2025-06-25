# utils/helpers.py
import os
from datetime import datetime
import json

# Paths
USER_FILE = "users.json"
LOG_FILE = "user_log.txt"
ACTIVE_SEASON_FILE = "active_season.txt"

# === User Management ===

def load_users():
    """Load user data from JSON file."""
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    """Save user data to JSON file."""
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

# === Logging ===

def log_activity(username, action):
    """Log user actions with timestamp."""
    with open(LOG_FILE, "a") as file:
        file.write(f"{datetime.now()} - {username} {action}\n")

# === Active Season Management ===

def get_active_season():
    """Get the currently active season."""
    try:
        with open(ACTIVE_SEASON_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "2024/25"  # Default fallback season

def set_active_season(season):
    """Set the active season."""
    with open(ACTIVE_SEASON_FILE, "w") as f:
        f.write(season)

# modules/ai_farm_manager.py

import pandas as pd
from datetime import datetime
from pathlib import Path
import os

# Allow override via environment variable
DATA_FOLDER = Path(os.getenv("AI_DATA_DIR", "data"))

SUGARCANE_SCHEDULE = {
    1: ["Gleaning"],
    2: ["Herbicide Application"],
    6: ["Gap Filling"],
    8: ["First Rouging"],
    9: ["First Fertilizer"],
    10: ["Second Rouging"],
    12: ["Second Fertilizer"],
    14: ["Third Rouging"],
    16: ["Third Fertilizer"],
    20: ["Weeding"],
    24: ["Monitoring"],
    32: ["Ripener Application"],
    44: ["Harvest Preparation"]
}

IRRIGATION_NOTE = "Irrigation: 12–15 applications over 10 months"


def get_weekly_activities(weeks_since_harvest: int):
    """
    Return the list of AI-suggested activities for a given week since harvest.
    Ensures activities are deduplicated while preserving order.
    """
    activities = []

    if 1 <= weeks_since_harvest <= 44:
        activities.append(IRRIGATION_NOTE)

    for week, tasks in SUGARCANE_SCHEDULE.items():
        if weeks_since_harvest >= week:
            activities.extend(tasks)

    if not activities:
        return ["Monitoring / General Maintenance"]

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for act in activities:
        if act not in seen:
            deduped.append(act)
            seen.add(act)

    return deduped


def get_growth_phase(weeks: int) -> str:
    """Map weeks since harvest to growth stage labels."""
    if weeks <= 4:
        return "🌱 Germination"
    elif 5 <= weeks <= 12:
        return "🌿 Tillering"
    elif 13 <= weeks <= 28:
        return "🌾 Grand Growth"
    elif 29 <= weeks <= 44:
        return "🍂 Maturity"
    else:
        return "🚜 Harvest Ready"


def ai_farm_manager_programme():
    """
    Generate AI-based weekly programme based on harvesting_records.xlsx.
    Returns a list of dicts with Field, Last Harvest, Weeks Since Harvest, Stage, and Activities.
    """

    harvesting_file = DATA_FOLDER / "harvesting_records.xlsx"
    if not harvesting_file.exists():
        return []

    df_harvest = pd.read_excel(harvesting_file)

    # Ensure required columns exist
    required = {"Field", "Date"}
    if not required.issubset(df_harvest.columns):
        return []

    # Parse and clean dates
    df_harvest["Date"] = pd.to_datetime(df_harvest["Date"], errors="coerce")
    df_harvest = df_harvest.dropna(subset=["Date"])

    if df_harvest.empty:
        return []

    # Keep only the latest harvest per field
    df_harvest = df_harvest.sort_values("Date").drop_duplicates("Field", keep="last")

    today = datetime.today().date()
    programme = []

    for _, row in df_harvest.iterrows():
        field = row["Field"]
        event_date = row["Date"].date()

        # More accurate week calculation
        weeks_since_harvest = (today - event_date).days // 7

        activities = get_weekly_activities(weeks_since_harvest)
        stage_label = get_growth_phase(weeks_since_harvest)

        programme.append({
            "Field": field,
            "Last Harvest": event_date,
            "Weeks Since Harvest": weeks_since_harvest,
            "Stage": stage_label,
            "AI Suggested Activities": ", ".join(activities)
        })

    return programme

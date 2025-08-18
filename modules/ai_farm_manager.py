import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

DATA_FOLDER = "data"

# 📅 Sugarcane activity schedule (weeks after harvest)
SUGARCANE_SCHEDULE = {
    1: ["Gleaning", "Soil Sampling (every 3 yrs)", "Repairing field damage", "Irrigation feeder maintain"],
    2: ["Return Irrigation (max 7 days)", "Middle Busting", "1st Fert application", "Gap Filling", "Pre-Emerg Herbicide application"],
    6: ["1st Rouging"],
    6: ["1st Hand Weeding (week 6-8)"],
    8: ["2nd Fert application (week 8-10)"],
    9: ["Leaf Sampling (week 9-10)"],
    10: ["2nd Rouging (week 10-12)"],
    12: ["2nd Hand Weeding (week 12-14)"],
    14: ["3rd Hand Weeding (optional, week 14-16)"],
    16: ["3rd Rouging (week 16-18)"],
    30: ["Order Inputs for next season (week 30-32)"],
    40: ["Ripener application (optional, week 40-42)", "Dry off (week 40-42)"],
    46: ["Harvest Prep (week 46-50)"],
}

# Constant: Irrigation is continuous
IRRIGATION_NOTE = "Irrigation: 12–15 applications over 10 months"


def get_weekly_activities(weeks_since_harvest: int) -> list:
    """Return activities for a given week since harvest."""
    activities = []

    # Add irrigation always (ongoing)
    if 1 <= weeks_since_harvest <= 44:
        activities.append(IRRIGATION_NOTE)

    # Match activities for this week
    for week, tasks in SUGARCANE_SCHEDULE.items():
        if weeks_since_harvest >= week:
            # Add week-ranged activities when valid
            activities.extend(tasks)

    return activities if activities else ["Monitoring / General Maintenance"]


def ai_farm_manager_programme() -> list:
    harvesting_file = os.path.join(DATA_FOLDER, "harvesting_records.xlsx")
    if not os.path.exists(harvesting_file):
        return []

    df_harvest = pd.read_excel(harvesting_file)
    df_harvest["Date"] = pd.to_datetime(df_harvest["Date"], errors="coerce")
    df_harvest = df_harvest.dropna(subset=["Date"])

    # Keep latest harvest per field
    latest_harvesting = df_harvest.sort_values("Date").drop_duplicates("Field", keep="last")

    today = datetime.today()
    programme = []

    for _, row in latest_harvesting.iterrows():
        field = row["Field"]
        event_date = row["Date"]

        delta = relativedelta(today, event_date)
        weeks_since_harvest = delta.years * 52 + delta.months * 4 + delta.days // 7

        activities = get_weekly_activities(weeks_since_harvest)

        stage_label = f"Week {weeks_since_harvest}"
        if weeks_since_harvest not in SUGARCANE_SCHEDULE:
            stage_label = "Other / Beyond Schedule"  # catch-all

        programme.append({
            "Field": field,
            "Last Harvest": event_date.date(),
            "Weeks Since Harvest": weeks_since_harvest,
            "Stage": stage_label,
            "AI Suggested Activities": ", ".join(activities)
        })

    return programme

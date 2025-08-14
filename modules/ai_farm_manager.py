import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

DATA_FOLDER = "data"

# 🌾 Determine crop stage based on months since planting/harvesting
def determine_crop_stage(months_since_planting: int) -> str:
    if months_since_planting < 2:
        return "🌱 Germination"
    elif months_since_planting < 5:
        return "🌿 Tillering"
    elif months_since_planting < 9:
        return "🌾 Grand Growth"
    elif months_since_planting < 11:
        return "🍂 Maturity"
    else:
        return "🚜 Harvest Ready"

# 🤖 AI-suggested activities for each crop stage
def get_ai_activities_for_stage(crop_stage: str) -> list:
    stage_schedule = {
        '🌱 Germination': ['Irrigation', 'Early Weeding'],
        '🌿 Tillering': ['Weeding', 'Fertilization'],
        '🌾 Grand Growth': ['Fertilization', 'Pest Control', 'Irrigation'],
        '🍂 Maturity': ['Ripener Application', 'Monitoring'],
        '🚜 Harvest Ready': ['Harvest Prep', 'Harvest'],
    }
    return stage_schedule.get(crop_stage, ['Monitoring'])

# 📅 Generate AI Farm Manager weekly programme
def ai_farm_manager_programme() -> list:
    planting_file = os.path.join(DATA_FOLDER, "planting_records.xlsx")
    harvesting_file = os.path.join(DATA_FOLDER, "harvesting_records.xlsx")

    # If files are missing, return empty programme
    if not os.path.exists(planting_file) or not os.path.exists(harvesting_file):
        return []

    # Read files safely
    df_plant = pd.read_excel(planting_file)
    df_harvest = pd.read_excel(harvesting_file)

    # Ensure Date column is datetime
    df_plant["Date"] = pd.to_datetime(df_plant["Date"], errors="coerce")
    df_harvest["Date"] = pd.to_datetime(df_harvest["Date"], errors="coerce")

    # Drop invalid rows
    df_plant = df_plant.dropna(subset=["Date"])
    df_harvest = df_harvest.dropna(subset=["Date"])

    # Get latest records per field
    latest_planting = df_plant.sort_values("Date").drop_duplicates("Field", keep="last")
    latest_harvesting = df_harvest.sort_values("Date").drop_duplicates("Field", keep="last")

    today = datetime.today()
    programme = []

    # Merge and find latest event for each field
    all_fields = pd.concat([
        latest_planting[["Field", "Date"]].assign(Source="Planting"),
        latest_harvesting[["Field", "Date"]].assign(Source="Harvesting")
    ])
    all_fields = all_fields.sort_values("Date").drop_duplicates("Field", keep="last")

    # Build programme
    for _, row in all_fields.iterrows():
        field = row["Field"]
        event_date = row["Date"]

        months_since_event = (
            relativedelta(today, event_date).months +
            relativedelta(today, event_date).years * 12
        )

        crop_stage = determine_crop_stage(months_since_event)
        activities = get_ai_activities_for_stage(crop_stage)

        programme.append({
            "Field": field,
            "Last Event": row["Source"],
            "Event Date": event_date.date(),
            "Months Since": months_since_event,
            "Stage": crop_stage,
            "AI Suggested Activities": ", ".join(activities)
        })

    return programme

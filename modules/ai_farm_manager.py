# modules/ai_farm_manager.py

import pandas as pd
from datetime import datetime
from pathlib import Path
import os

# ------------------------
# Data folder configuration
# ------------------------
DATA_FOLDER = Path(os.getenv("AI_DATA_DIR", "data"))

# ------------------------
# Sugarcane AI Schedule
# ------------------------
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

# ------------------------
# Helper functions
# ------------------------
def get_growth_phase(weeks: int) -> str:
    """Map weeks since planting/harvest to growth stage labels."""
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


def get_weekly_activities(weeks_since: int):
    """Return a list of AI-suggested activities for a given week."""
    activities = []

    if 1 <= weeks_since <= 44:
        activities.append(IRRIGATION_NOTE)

    for week, tasks in SUGARCANE_SCHEDULE.items():
        if weeks_since >= week:
            activities.extend(tasks)

    if not activities:
        activities = ["Monitoring / General Maintenance"]

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for act in activities:
        if act not in seen:
            deduped.append(act)
            seen.add(act)

    return deduped

# ------------------------
# Main AI Programme
# ------------------------
def ai_farm_manager_programme():
    """
    Generate AI-based weekly programme combining planting and harvesting records.
    Returns a list of dicts ready for Flask rendering.
    """

    planting_file = DATA_FOLDER / "planting_records.xlsx"
    harvesting_file = DATA_FOLDER / "harvesting_records.xlsx"

    # Load data safely
    planting_df = pd.read_excel(planting_file) if planting_file.exists() else pd.DataFrame()
    harvesting_df = pd.read_excel(harvesting_file) if harvesting_file.exists() else pd.DataFrame()

    # Normalize and clean dates
    if not planting_df.empty:
        planting_df.columns = planting_df.columns.str.strip()
        if "Planting Date" in planting_df.columns:
            planting_df.rename(columns={"Planting Date": "Date"}, inplace=True)
        planting_df["Date"] = pd.to_datetime(planting_df["Date"], errors="coerce")

    if not harvesting_df.empty:
        harvesting_df.columns = harvesting_df.columns.str.strip()
        if "Harvest Date" in harvesting_df.columns:
            harvesting_df.rename(columns={"Harvest Date": "Date"}, inplace=True)
        harvesting_df["Date"] = pd.to_datetime(harvesting_df["Date"], errors="coerce")

    # Combine datasets
    combined = pd.concat(
        [
            planting_df[["Field", "Date"]].assign(Source="Planting") if not planting_df.empty else pd.DataFrame(),
            harvesting_df[["Field", "Date"]].assign(Source="Harvesting") if not harvesting_df.empty else pd.DataFrame(),
        ],
        ignore_index=True
    )

    if combined.empty:
        return []

    # Keep latest activity per field
    combined = combined.dropna(subset=["Date"])
    combined = combined.sort_values("Date").drop_duplicates("Field", keep="last")

    today = datetime.today().date()
    programme = []

    for _, row in combined.iterrows():
        field = row["Field"]
        event_date = row["Date"].date()
        source = row["Source"]

        # Weeks since last activity
        weeks_since = (today - event_date).days // 7

        # Stage & activities
        stage_label = get_growth_phase(weeks_since)
        activities = get_weekly_activities(weeks_since)

        # Ensure activities is always a list
        if isinstance(activities, str):
            activities = [activities]
        elif activities is None:
            activities = ["Monitoring / General Maintenance"]

        # Add planting-specific note for very young crops
        if source == "Planting" and weeks_since < 4:
            activities.insert(0, "Germination observation and weed control")

        # Make sure everything is a string
        activities = [str(act) for act in activities]

        programme.append({
            "Field": field,
            "Last Activity": event_date,
            "Weeks Since": weeks_since,
            "Stage": stage_label,
            "Recommended Activities": ", ".join(activities),
            "Record Source": source
        })

    return programme

# modules/ai_farm_manager.py
import os
import openai

# Get API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def ai_answer_query(question: str) -> str:
    if not question.strip():
        return "❌ Please ask a question."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if available
            messages=[
                {"role": "system", "content": "You are a helpful AI Farm Manager. Answer questions about farming, crop yields, irrigation, fertilizer, and farm operations."},
                {"role": "user", "content": question}
            ],
            max_tokens=300,
            temperature=0.5
        )
        answer = response.choices[0].message['content'].strip()
        return answer

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "❌ Error contacting AI."

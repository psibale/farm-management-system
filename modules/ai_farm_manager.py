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
    activities = []

    if 1 <= weeks_since <= 44:
        activities.append(IRRIGATION_NOTE)

    for week, tasks in SUGARCANE_SCHEDULE.items():
        if weeks_since >= week:
            activities.extend(tasks)

    if not activities:
        activities = ["Monitoring / General Maintenance"]

    seen = set()
    deduped = []
    for act in activities:
        if act not in seen:
            deduped.append(act)
            seen.add(act)

    return deduped

# ------------------------
# AI Programme Generation
# ------------------------
def ai_farm_manager_programme():
    planting_file = DATA_FOLDER / "planting_records.xlsx"
    harvesting_file = DATA_FOLDER / "harvesting_records.xlsx"

    planting_df = pd.read_excel(planting_file) if planting_file.exists() else pd.DataFrame()
    harvesting_df = pd.read_excel(harvesting_file) if harvesting_file.exists() else pd.DataFrame()

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

    combined = pd.concat(
        [
            planting_df[["Field", "Date"]].assign(Source="Planting") if not planting_df.empty else pd.DataFrame(),
            harvesting_df[["Field", "Date"]].assign(Source="Harvesting") if not harvesting_df.empty else pd.DataFrame(),
        ],
        ignore_index=True
    )

    if combined.empty:
        return []

    combined = combined.dropna(subset=["Date"])
    combined = combined.sort_values("Date").drop_duplicates("Field", keep="last")

    today = datetime.today().date()
    programme = []

    for _, row in combined.iterrows():
        field = row["Field"]
        event_date = row["Date"].date()
        source = row["Source"]

        weeks_since = (today - event_date).days // 7

        stage_label = get_growth_phase(weeks_since)
        activities = get_weekly_activities(weeks_since)

        if isinstance(activities, str):
            activities = [activities]
        elif activities is None:
            activities = ["Monitoring / General Maintenance"]

        if source == "Planting" and weeks_since < 4:
            activities.insert(0, "Germination observation and weed control")

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

# ------------------------
# OPENAI FIXED SECTION
# ------------------------
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_answer_query(question: str) -> str:
    if not question.strip():
        return "❌ Please ask a question."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or gpt-4o, gpt-4.1, etc.
            messages=[
                {"role": "system", "content": "You are a helpful AI Farm Manager. Answer questions about farming, crop yields, irrigation, fertilizer, and farm operations."},
                {"role": "user", "content": question}
            ],
            max_tokens=300,
            temperature=0.5
        )

        # NEW RESPONSE FORMAT
        answer = response.choices[0].message.content
        return answer.strip()

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "❌ Error contacting AI."

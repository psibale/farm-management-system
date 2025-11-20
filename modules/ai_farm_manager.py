import pandas as pd
from datetime import datetime
from pathlib import Path
import os
from openai import OpenAI


def get_parent_block(field):
    """
    Convert field like DG01007 → DG01000.
    Rule: first 5 characters + '00'
    """
    try:
        return field[:5] + "00"
    except:
        return field

# -------------------------------------------------
# 1. CONFIG
# -------------------------------------------------
DATA_FOLDER = Path(os.getenv("AI_DATA_DIR", "data"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------
# 2. AUTO-LOAD ANY EXCEL FILE IN /data
# -------------------------------------------------
def load_all_data():
    data = {}
    for file in DATA_FOLDER.glob("*.xlsx"):
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            data[file.stem] = df
        except Exception as e:
            print(f"Failed to load {file}: {e}")
    return data

# -------------------------------------------------
# 3. FIELD SUMMARY BUILDER (AI context)
# -------------------------------------------------
def build_field_context(data_dict):
    """
    Convert your farm data into readable text for AI reasoning.
    """
    sections = []

    for name, df in data_dict.items():
        # Limit AI context to first 20 rows
        preview = df.head(20).to_string(index=False)
        sections.append(f"\n### FILE: {name}\n{preview}")

    return "\n\n".join(sections)

# -------------------------------------------------
# 4. AI QUERY HANDLER
# -------------------------------------------------
def ai_answer_query(question: str) -> str:
    if not question.strip():
        return "❌ Please ask a question."

    try:
        # Load all farm datasets
        farm_data = load_all_data()

        # Convert to text for AI context
        context = build_field_context(farm_data)

        # Prompt sent to OpenAI
        prompt = f"""
You are an intelligent Farm AI Manager for a sugarcane estate.

You have access to the following dataset previews:

{context}

INSTRUCTIONS:
- Use the available data to answer accurately.
- If data is missing, say so.
- Provide practical field-level recommendations.
- Analyse fertilizer logs, irrigation, weeding, stress, diseases, planting, harvesting, yield, ERS, etc.
- Be precise and helpful.

QUESTION:
{question}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a smart AI Farm Manager."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=600
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return f"❌ Error contacting AI: {e}"

# -------------------------------------------------
# 5. FIELD PROGRAMME LOGIC
# -------------------------------------------------

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

    # irrigation applies early
    if 1 <= weeks_since <= 44:
        activities.append(IRRIGATION_NOTE)

    for week, tasks in SUGARCANE_SCHEDULE.items():
        if weeks_since >= week:
            activities.extend(tasks)

    if not activities:
        activities = ["Monitoring / General Maintenance"]

    # remove duplicates
    return list(dict.fromkeys(activities))

# -------------------------------------------------
# 6. MAIN PROGRAMME GENERATOR — REQUIRED BY YOUR SYSTEM
# -------------------------------------------------
def ai_farm_manager_programme():
    """
    This function MUST exist because programme.py imports it.
    Generates weekly crop programme per field.
    """

    planting_file = DATA_FOLDER / "planting_records.xlsx"
    harvesting_file = DATA_FOLDER / "harvesting_records.xlsx"

    planting_df = pd.read_excel(planting_file) if planting_file.exists() else pd.DataFrame()
    harvesting_df = pd.read_excel(harvesting_file) if harvesting_file.exists() else pd.DataFrame()

    # Clean column names
    for df in (planting_df, harvesting_df):
        if not df.empty:
            df.columns = df.columns.str.strip()

    if not planting_df.empty and "Planting Date" in planting_df.columns:
        planting_df.rename(columns={"Planting Date": "Date"}, inplace=True)

    if not harvesting_df.empty and "Harvest Date" in harvesting_df.columns:
        harvesting_df.rename(columns={"Harvest Date": "Date"}, inplace=True)

    # Ensure dates are datetime
    if not planting_df.empty:
        planting_df["Date"] = pd.to_datetime(planting_df["Date"], errors="coerce")

    if not harvesting_df.empty:
        harvesting_df["Date"] = pd.to_datetime(harvesting_df["Date"], errors="coerce")

    # Combine: planting & harvesting, keep latest event per field
    combined = pd.concat([
        planting_df[["Field", "Date"]].assign(Source="Planting") if not planting_df.empty else pd.DataFrame(),
        harvesting_df[["Field", "Date"]].assign(Source="Harvesting") if not harvesting_df.empty else pd.DataFrame(),
    ], ignore_index=True)

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

        # Germination-specific task
        if source == "Planting" and weeks_since < 4:
            activities.insert(0, "Germination observation & weed control")

        parent_block = get_parent_block(field)

        programme.append({
            "Field": field,
            "Parent Block": parent_block,
            "Last Activity": event_date,
            "Weeks Since": weeks_since,
            "Stage": stage_label,
            "Recommended Activities": ", ".join(activities),
            "Record Source": source
        })

    return programme

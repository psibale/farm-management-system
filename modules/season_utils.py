import pandas as pd
from datetime import datetime
import os

SEASON_FILE = "data/season_data.xlsx"


def get_active_season():

    if not os.path.exists(SEASON_FILE):
        raise FileNotFoundError("season_data.xlsx not found.")

    df = pd.read_excel(SEASON_FILE)

    # Ensure required columns exist
    required_cols = ["Season Name", "Start Date", "End Date"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing column in season_data.xlsx: {col}")

    df["Start Date"] = pd.to_datetime(df["Start Date"])
    df["End Date"] = pd.to_datetime(df["End Date"])

    today = datetime.today()

    active = df[
        (df["Start Date"] <= today) &
        (df["End Date"] >= today)
    ]

    if active.empty:
        raise ValueError("No active season found for today's date.")

    return active.iloc[0]["Season Name"]
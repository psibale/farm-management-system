import os
import pandas as pd

DATA_FOLDER = "data"

def safe_float(value):

    try:

        if pd.isna(value):
            return 0.0

        return float(value)

    except Exception:

        return 0.0


def safe_int(value):

    try:

        if pd.isna(value):
            return 0

        return int(value)

    except Exception:

        return 0


def safe_string(value):

    try:

        if pd.isna(value):
            return ""

        return str(value)

    except Exception:

        return ""

def load_excel(filename):

    path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_excel(path)

    except Exception:
        return pd.DataFrame()


def get_weather_information():

    df = load_excel("weather_data.xlsx")

    if df.empty:
        return {}

    # ----------------------------
    # Active Season
    # ----------------------------

    try:

        from modules.season import get_active_season

        season = get_active_season()

        if "Season" in df.columns:
            df = df[df["Season"] == season]
        if df.empty:
            return {}

    except Exception:
        pass

    if df.empty:
        return {}

    # Convert all dates to datetime
    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    # Remove invalid dates
    df = df.dropna(subset=["Date"])

    if df.empty:
        return {}

    df = df.sort_values("Date")

    row = df.iloc[-1]

    date = row.get("Date", "")

    if pd.notna(date):
        date = pd.to_datetime(date).strftime("%d-%b-%Y")
    else:
        date = ""

    return {

        "date": date,

        "rainfall": float(row.get("Rainfall", 0) or 0),

        "evapotranspiration": float(
            row.get("Evapotranspiration", 0) or 0
        ),

        "temperature": float(
            row.get("Temperature", 0) or 0
        )

    }
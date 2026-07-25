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


def get_irrigation_information(field_name):

    df = load_excel("irrigation_records.xlsx")

    if df.empty:
        return {}

    # -----------------------------
    # Active Season
    # -----------------------------

    try:

        from modules.season import get_active_season

        season = get_active_season()

        if "Season" in df.columns:
            df = df[df["Season"] == season]
        if df.empty:
            return {}

    except Exception:
        pass

    # -----------------------------
    # Main Field + Sub-fields
    # -----------------------------

    registered = load_excel("registered_fields.xlsx")

    sub_fields = [field_name]

    if not registered.empty:

        sub_fields = registered[
            registered["Main Field"] == field_name
        ]["Field"].tolist()

        if field_name not in sub_fields:
            sub_fields.append(field_name)

    rows = df[df["Field"].isin(sub_fields)]

    if rows.empty:

        return {

            "status": "No Irrigation",

            "last_irrigation": "",

            "applications": 0,

            "total_applied": 0

        }

    rows = rows.sort_values("Date")

    last = rows.iloc[-1]

    date = last["Date"]

    if pd.notna(date):
        date = pd.to_datetime(date).strftime("%d-%b-%Y")
    else:
        date = ""

    return {

        "status": "Irrigated",

        "last_irrigation": date,

        "applications": len(rows),

        "total_applied": round(
            rows["Irrigation Applied"].fillna(0).sum(),
            2
        )

    }
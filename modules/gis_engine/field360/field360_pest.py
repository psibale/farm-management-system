import os
import pandas as pd

DATA_FOLDER = "data"


# --------------------------------
# SAFE CONVERSION FUNCTIONS
# --------------------------------

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


# --------------------------------
# LOAD EXCEL
# --------------------------------

def load_excel(filename):

    path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_excel(path)

    except Exception:
        return pd.DataFrame()


# --------------------------------
# PEST INFORMATION
# --------------------------------

def get_pest_information(field_name):

    df = load_excel("pest_disease_control.xlsx")

    if df.empty:
        return {}

    # --------------------------------
    # Active Season
    # --------------------------------

    try:

        from modules.season import get_active_season

        season = get_active_season()

        if "Season" in df.columns:
            df = df[df["Season"] == season]

        if df.empty:
            return {}

    except Exception:
        pass

    # --------------------------------
    # Main Field + Sub-fields
    # --------------------------------

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

            "status": "No Inspection"

        }

    rows = rows.sort_values("Date")

    row = rows.iloc[-1]

    # --------------------------------
    # Date
    # --------------------------------

    date = row.get("Date")

    if pd.notna(date):
        date = pd.to_datetime(date).strftime("%d-%b-%Y")
    else:
        date = ""

    # --------------------------------
    # Pest Levels
    # --------------------------------

    smut = safe_float(row.get("SMUT%"))

    ysa = safe_float(row.get("YSA%"))

    beetles = safe_int(row.get("Black Beetles (ha)"))

    if smut == 0 and ysa == 0 and beetles == 0:

        status = "Healthy"

    elif smut < 5 and ysa < 5:

        status = "Monitor"

    else:

        status = "Treatment Required"

    # --------------------------------
    # Return
    # --------------------------------

    return {

        "status": status,

        "last_inspection": date,

        "smut": smut,

        "ysa": ysa,

        "black_beetles": beetles,

        "lady_beetles": safe_int(row.get("Lady Beetle")),

        "hectares": safe_float(row.get("Hectares")),

        "pesticide": safe_string(row.get("Pesticide Used")),

        "liters": safe_float(row.get("Liters")),

        "mandays": safe_int(row.get("Mandays"))

    }
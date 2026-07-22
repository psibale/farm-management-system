import os
import pandas as pd

DATA_FOLDER = "data"

def safe_int(value):

    try:
        return int(value)

    except Exception:
        return 0


def safe_float(value):

    try:
        return float(value)

    except Exception:
        return 0.0

# -------------------------------------------------
# SAFE EXCEL LOADER
# -------------------------------------------------

def load_excel(filename):

    path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_excel(path)

    except Exception:
        return pd.DataFrame()


# -------------------------------------------------
# HARVEST INFORMATION
# -------------------------------------------------

def get_harvest_information(field_name):

    df = load_excel("harvesting_records.xlsx")

    if df.empty:
        return {
            "status": "Not Harvested"
        }

    # --------------------------------------------
    # ACTIVE SEASON
    # --------------------------------------------

    try:

        from modules.season import get_active_season

        season = get_active_season()

        if "Season" in df.columns:

            df = df[df["Season"] == season]

    except Exception:
        pass

    # --------------------------------------------
    # CHECK FIELD COLUMN
    # --------------------------------------------

    if "Field" not in df.columns:

        return {
            "status": "Not Harvested"
        }

    # --------------------------------------------
    # FIND ALL SUB-FIELDS
    # --------------------------------------------

    registered = load_excel("registered_fields.xlsx")

    sub_fields = [field_name]

    if not registered.empty:
        sub_fields = registered[
            registered["Main Field"] == field_name
            ]["Field"].tolist()

    # --------------------------------------------
    # FILTER HARVEST RECORDS
    # --------------------------------------------

    rows = df[df["Field"].isin(sub_fields)]

    if rows.empty:
        return {
            "status": "Not Harvested"
        }

    # --------------------------------------------
    # LATEST HARVEST
    # --------------------------------------------

    rows = rows.sort_values("Date")

    row = rows.iloc[-1]

    # --------------------------------------------
    # FORMAT DATE
    # --------------------------------------------

    date = row.get("Date", "")

    if pd.notna(date):

        date = pd.to_datetime(date).strftime("%d-%b-%Y")

    else:

        date = ""

    # --------------------------------------------
    # RETURN DATA
    # --------------------------------------------

    return {

        "status": "Harvested",

        "last_harvest": date,

        "crop_type": row.get("Crop Type", ""),

        "harvested_area": safe_float(row.get("Harvested Area (ha)")),

        # Daily harvested tons (Bundles × 6)
        "daily_harvest_tons": safe_float(row.get("Yield (Tons)")),

        "bundles": safe_int(row.get("Bundles")),

        "mandays": safe_int(row.get("Mandays")),

        "employees": {

            "foreman": safe_int(row.get("Foreman")),

            "capitaos": safe_int(row.get("Capitaos")),

            "water_drawers": safe_int(row.get("Water Drawers")),

            "dippers": safe_int(row.get("Dippers")),

            "needlemen": safe_int(row.get("Needlemen")),

            "bicycle_guards": safe_int(row.get("Bicycle Guards")),

            "feeder_breakers": safe_int(row.get("Feeder Breakers")),

            "cane_cutters": safe_int(row.get("Cane Cutters")),

            "first_aider": safe_int(row.get("First-Aider")),

            "she_representative": safe_int(row.get("SHE Representative")),

            "fire_team": safe_int(row.get("Fire Team"))

        }

    }
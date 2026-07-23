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

    if (
        not registered.empty
        and "Main Field" in registered.columns
        and "Field" in registered.columns
    ):

        sub_fields = registered[
            registered["Main Field"] == field_name
        ]["Field"].dropna().tolist()

        if not sub_fields:
            sub_fields = [field_name]

    # --------------------------------------------
    # FILTER HARVEST RECORDS
    # --------------------------------------------

    rows = df[df["Field"].isin(sub_fields)]

    if rows.empty:
        return {
            "status": "Not Harvested"
        }

    rows = rows.sort_values("Date")

    latest = rows.iloc[-1]

    # --------------------------------------------
    # LAST HARVEST DATE
    # --------------------------------------------

    date = latest.get("Date", "")

    if pd.notna(date):
        date = pd.to_datetime(date).strftime("%d-%b-%Y")
    else:
        date = ""

    # --------------------------------------------
    # SUMMARIES
    # --------------------------------------------

    harvested_area = rows["Harvested Area (ha)"].fillna(0).sum()

    daily_harvest = rows["Yield (Tons)"].fillna(0).sum()

    bundles = rows["Bundles"].fillna(0).sum()

    mandays = rows["Mandays"].fillna(0).sum()

    foreman = rows["Foreman"].fillna(0).sum()

    capitaos = rows["Capitaos"].fillna(0).sum()

    water_drawers = rows["Water Drawers"].fillna(0).sum()

    dippers = rows["Dippers"].fillna(0).sum()

    needlemen = rows["Needlemen"].fillna(0).sum()

    bicycle_guards = rows["Bicycle Guards"].fillna(0).sum()

    feeder_breakers = rows["Feeder Breakers"].fillna(0).sum()

    cane_cutters = rows["Cane Cutters"].fillna(0).sum()

    first_aider = rows["First-Aider"].fillna(0).sum()

    she_representative = rows["SHE Representative"].fillna(0).sum()

    fire_team = rows["Fire Team"].fillna(0).sum()

    # --------------------------------------------
    # RETURN
    # --------------------------------------------

    return {

        "status": "Harvested",

        "last_harvest": date,

        "crop_type": latest.get("Crop Type", ""),

        "harvested_area": safe_float(harvested_area),

        "daily_harvest_tons": safe_float(daily_harvest),

        "bundles": safe_int(bundles),

        "mandays": safe_int(mandays),

        "employees": {

            "foreman": safe_int(foreman),

            "capitaos": safe_int(capitaos),

            "water_drawers": safe_int(water_drawers),

            "dippers": safe_int(dippers),

            "needlemen": safe_int(needlemen),

            "bicycle_guards": safe_int(bicycle_guards),

            "feeder_breakers": safe_int(feeder_breakers),

            "cane_cutters": safe_int(cane_cutters),

            "first_aider": safe_int(first_aider),

            "she_representative": safe_int(she_representative),

            "fire_team": safe_int(fire_team)

        }

    }
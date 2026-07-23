import os
import pandas as pd

DATA_FOLDER = "data"


# -------------------------------------------------
# SAFE FUNCTIONS
# -------------------------------------------------

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
# ACTUAL YIELD
# -------------------------------------------------

def get_actual_yield(field_name):

    df = load_excel("yield_data.xlsx")

    if df.empty:

        return {
            "actual": 0.0
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
    # FIND SUB-FIELDS
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
    # FILTER
    # --------------------------------------------

    if "Field" not in df.columns:

        return {
            "actual": 0.0
        }

    rows = df[df["Field"].isin(sub_fields)]

    if rows.empty:

        return {
            "actual": 0.0
        }

    # --------------------------------------------
    # FIND THE YIELD COLUMN
    # --------------------------------------------

    possible_columns = [

        "Yield (Tons)",
        "Actual Yield",
        "Actual Yield (Tons)",
        "Tons",
        "Tonnes"

    ]

    yield_column = None

    for col in possible_columns:

        if col in rows.columns:

            yield_column = col
            break

    if yield_column is None:

        return {
            "actual": 0.0
        }

    actual = rows[yield_column].fillna(0).sum()

    return {

        "actual": safe_float(rows["Yield (Tons)"].fillna(0).sum()),

        "bundles": int(rows["Bundles"].fillna(0).sum()),

        "deliveries": len(rows),

        "last_delivery": (
            pd.to_datetime(rows["Date"].max()).strftime("%d-%b-%Y")
            if "Date" in rows.columns and not rows.empty
            else ""
        )

    }
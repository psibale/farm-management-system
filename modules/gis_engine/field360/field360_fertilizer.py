import os
import pandas as pd

DATA_FOLDER = "data"


# --------------------------------------------
# HELPERS
# --------------------------------------------

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


# --------------------------------------------
# LOAD EXCEL
# --------------------------------------------

def load_excel(filename):

    path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_excel(path)
    except Exception:
        return pd.DataFrame()


# --------------------------------------------
# FERTILIZER INFORMATION
# --------------------------------------------

def get_fertilizer_information(field_name):

    df = load_excel("fertilizer_records.xlsx")

    if df.empty:
        return {
            "status": "No Application"
        }

    # --------------------------------------------
    # ACTIVE SEASON
    # --------------------------------------------

    try:
        from modules.season import get_active_season

        season = get_active_season()

        if "Season" in df.columns:
            df = df[df["Season"] == season]

        if df.empty:
            return {
                "status": "No Application"
            }

    except Exception:
        pass

    # --------------------------------------------
    # MAIN FIELD + SUBFIELDS
    # --------------------------------------------

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
            "status": "No Application"
        }

    # --------------------------------------------
    # LATEST APPLICATION
    # --------------------------------------------

    rows = rows.sort_values("Date")

    row = rows.iloc[-1]

    date = row.get("Date")

    if pd.notna(date):
        date = pd.to_datetime(date).strftime("%d-%b-%Y")
    else:
        date = ""

    # --------------------------------------------
    # TOTALS
    # --------------------------------------------

    total_area = safe_float(rows["Area (Ha)"].sum())

    dap = safe_float(rows["DAP"].sum())
    sa = safe_float(rows["SA"].sum())
    mop = safe_float(rows["MOP"].sum())
    zinc = safe_float(rows["Zinc"].sum())
    urea = safe_float(rows["UREA"].sum())

    total_fertilizer = dap + sa + mop + zinc + urea

    return {

        "status": "Applied",

        "last_application": date,

        "applications": len(rows),

        "area": total_area,

        "dap": dap,

        "sa": sa,

        "mop": mop,

        "zinc": zinc,

        "urea": urea,

        "total_fertilizer": total_fertilizer,

        "mandays": safe_int(rows["Mandays"].sum())

    }
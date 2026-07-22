import os
import pandas as pd

DATA_FOLDER = "data"


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
# FIELD INFORMATION
# -------------------------------------------------

def get_field_information(field_name):

    fields = load_excel("registered_fields.xlsx")

    if fields.empty:
        return {}

    try:

        from modules.season import get_active_season

        active_season = get_active_season()

        rows = fields[
            (fields["Main Field"] == field_name) &
            (fields["Season"] == active_season)
        ]

    except Exception:

        rows = fields[
            fields["Main Field"] == field_name
        ]

    if rows.empty:
        return {}

    row = rows.iloc[0]

    # -----------------------------
    # AREA FROM GIS
    # -----------------------------

    polygons = load_excel("field_polygons.xlsx")

    area = 0

    if not polygons.empty:

        poly = polygons[
            polygons["Field"] == field_name
        ]

        if not poly.empty:

            area = float(poly.iloc[0]["Area (Ha)"])

    return {

        "field": field_name,

        "season": row.get("Season", ""),

        "crop": row.get("Crop Name", ""),

        "soil": row.get("Soil Type", ""),

        "location": row.get("Location", ""),

        "crop_age": row.get("Crop Age", ""),

        "tam": row.get("TAM", ""),

        "area": area

    }
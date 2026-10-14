from flask import Blueprint, render_template, request, redirect, url_for, flash
import geopandas as gpd
from modules.utils import role_required
import traceback
from flask import jsonify
from modules.gis_engine.field360.field360 import build_field360
import numpy as np

gis_bp = Blueprint('gis', __name__)

# File paths
GIS_FILE = 'data/field_polygons.xlsx'
WEATHER_FILE = 'data/weather_data.xlsx'
IRRIGATION_FILE = 'data/irrigation_records.xlsx'
SUB_FIELDS_FILE = "data/sub_fields.xlsx"

def make_json_safe(obj):
    """
    Convert Pandas / NumPy values into
    standard Python JSON-compatible values.
    """

    if isinstance(obj, dict):

        return {
            str(key): make_json_safe(value)
            for key, value in obj.items()
        }


    if isinstance(obj, list):

        return [
            make_json_safe(value)
            for value in obj
        ]


    if isinstance(obj, tuple):

        return [
            make_json_safe(value)
            for value in obj
        ]


    if isinstance(obj, np.integer):

        return int(obj)


    if isinstance(obj, np.floating):

        return float(obj)


    if isinstance(obj, np.bool_):

        return bool(obj)


    if pd.isna(obj):

        return None


    return obj

# ==============================
# 🌍 AREA CALCULATION
# ==============================
def calculate_area_hectares(geojson):
    geom = shape(geojson['features'][0]['geometry'])
    gdf = gpd.GeoDataFrame(index=[0], geometry=[geom], crs="EPSG:4326")
    gdf = gdf.to_crs(epsg=3857)
    area_m2 = gdf['geometry'].area[0]
    return round(area_m2 / 10000, 2)


from shapely.geometry import shape
from pyproj import Transformer

def calculate_area_hectares(geojson_geom):
    """
    Converts lat/lng polygon → meters → hectares
    """

    geom = shape(geojson_geom)

    # Convert WGS84 → UTM (Africa zone approx)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32736", always_xy=True)

    def project(x, y):
        return transformer.transform(x, y)

    projected = shapely.ops.transform(project, geom)

    area_m2 = projected.area
    area_ha = area_m2 / 10000

    return round(area_ha, 2)

# ==============================
# 📊 LOAD DATA (PERFORMANCE FIX)
# ==============================
def load_data():
    weather = pd.read_excel(WEATHER_FILE)
    if os.path.exists(IRRIGATION_FILE):
        irrigation = pd.read_excel(IRRIGATION_FILE)
    else:
        irrigation = pd.DataFrame(
            columns=["Date", "Field", "Irrigation Applied"]
        )

    # Clean columns
    weather.columns = weather.columns.str.strip()
    irrigation.columns = irrigation.columns.str.strip()

    # Convert dates
    weather['Date'] = pd.to_datetime(weather['Date'])
    irrigation['Date'] = pd.to_datetime(irrigation['Date'])

    # Normalize field names
    if 'Field' in irrigation.columns:
        irrigation['Field'] = irrigation['Field'].astype(str).str.strip().str.lower()

    return weather, irrigation


def recalculate_field_stress_levels(start_date=None, end_date=None):
    """Recalculate and save stress labels using the GIS stress formula.

    When no date range is supplied, use the active April-to-current-date
    season. Weather and irrigation entry routes use this default so field
    colors stay current without a manual update form submission.
    """
    from datetime import date
    from modules.season import get_active_season

    if not os.path.exists(GIS_FILE):
        raise FileNotFoundError("Mapped field data is not available.")
    if not os.path.exists(WEATHER_FILE):
        raise FileNotFoundError("Weather data is not available yet.")

    today = date.today()
    if not start_date or not end_date:
        active_season = str(get_active_season() or "").strip()
        try:
            season_year = int(active_season.split("/")[0])
        except (TypeError, ValueError):
            season_year = today.year if today.month >= 4 else today.year - 1
        start_date = date(season_year, 4, 1)
        end_date = today

    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start) or pd.isna(end):
        raise ValueError("A valid stress calculation date range is required.")

    fields_df = pd.read_excel(GIS_FILE)
    fields_df.columns = fields_df.columns.astype(str).str.strip()
    if "Field" not in fields_df.columns:
        raise ValueError("GIS file is missing the 'Field' column.")

    weather = pd.read_excel(WEATHER_FILE)
    weather.columns = weather.columns.astype(str).str.strip()
    required_weather = {"Date", "Rainfall", "Evapotranspiration"}
    if not required_weather.issubset(weather.columns):
        raise ValueError("Weather data is missing required stress calculation columns.")
    weather["Date"] = pd.to_datetime(weather["Date"], errors="coerce").dt.normalize()
    for column in ("Rainfall", "Evapotranspiration"):
        weather[column] = pd.to_numeric(weather[column], errors="coerce").fillna(0)
    weather = weather[
        weather["Date"].between(start.normalize(), end.normalize(), inclusive="both")
    ]

    if os.path.exists(IRRIGATION_FILE):
        irrigation = pd.read_excel(IRRIGATION_FILE)
        irrigation.columns = irrigation.columns.astype(str).str.strip()
        required_irrigation = {"Date", "Field", "Irrigation Applied"}
        if not required_irrigation.issubset(irrigation.columns):
            raise ValueError("Irrigation data is missing required stress calculation columns.")
        irrigation["Date"] = pd.to_datetime(irrigation["Date"], errors="coerce").dt.normalize()
        irrigation["_field_key"] = irrigation["Field"].astype(str).str.strip().str.casefold()
        irrigation["Irrigation Applied"] = pd.to_numeric(
            irrigation["Irrigation Applied"], errors="coerce"
        ).fillna(0)
        irrigation = irrigation[
            irrigation["Date"].between(start.normalize(), end.normalize(), inclusive="both")
        ]
    else:
        irrigation = pd.DataFrame(columns=["Date", "Field", "Irrigation Applied", "_field_key"])

    daily_weather = weather.groupby("Date")[["Rainfall", "Evapotranspiration"]].sum()
    if daily_weather.empty:
        raise ValueError("No weather entries are available for the selected stress date range.")
    days = pd.date_range(start.normalize(), min(end.normalize(), daily_weather.index.max()), freq="D")
    daily_weather = daily_weather.reindex(days, fill_value=0)
    fields_df["_base_field"] = fields_df["Field"].map(base_dg_field_name)
    stress_by_family = {}
    for base_name, family_fields in fields_df.groupby("_base_field", sort=False):
        names = family_fields["Field"].dropna().astype(str).str.strip().unique().tolist()
        areas = {
            str(row["Field"]).strip(): pd.to_numeric(row.get("Area (Ha)", 0), errors="coerce")
            for _, row in family_fields.iterrows()
        }
        areas = {name: float(area) if pd.notna(area) and area > 0 else 0 for name, area in areas.items()}
        irrigation_by_date = aggregate_field_irrigation_by_date(
            irrigation, names, areas, daily_weather.index
        )
        moisture_mm = calculate_soil_moisture_series(
            daily_weather, irrigation_by_date
        ).iloc[-1]
        stress_by_family[base_name] = classify_soil_moisture(float(moisture_mm))
    fields_df["Stress Level"] = fields_df["_base_field"].map(stress_by_family)
    fields_df = fields_df.drop(columns=["_base_field"])
    fields_df.to_excel(GIS_FILE, index=False)
    return len(fields_df)


SOIL_WATER_CAPACITY_MM = 100.0
INITIAL_SOIL_MOISTURE_MM = 5.0
CROP_ET_FACTOR = 1.0


def base_dg_field_name(field_name):
    """Return a road-split DG field's parent code, e.g. DG09000A -> DG09000."""
    import re

    value = str(field_name or "").strip()
    match = re.fullmatch(r"(DG\d+)[A-Z]", value, flags=re.IGNORECASE)
    return match.group(1).upper() if match else value


def aggregate_field_irrigation_by_date(irrigation, field_names, field_areas, dates):
    """Aggregate canonical and road-split irrigation into one parent-field series."""
    date_index = pd.DatetimeIndex(dates).normalize()
    names = {str(name).strip() for name in field_names if str(name).strip()}
    families = {base_dg_field_name(name).casefold() for name in names}
    selected = irrigation
    if not irrigation.empty and "Field" in irrigation.columns and families:
        selected = irrigation[
            irrigation["Field"].astype(str).map(base_dg_field_name).str.casefold().isin(families)
        ]
    family_names = names | (
        set(selected["Field"].dropna().astype(str).str.strip()) if not selected.empty else set()
    )
    parent_names = {base_dg_field_name(name).casefold() for name in family_names}
    split_names = {
        name for name in family_names
        if name.casefold() not in parent_names
    }
    components = split_names or family_names
    if not components:
        return pd.Series(0.0, index=date_index)

    areas = {str(name).strip().casefold(): float(area or 0) for name, area in field_areas.items()}
    component_areas = {name.casefold(): areas.get(name.casefold(), 0) for name in components}
    total_area = sum(area for area in component_areas.values() if area > 0)
    weights = {
        name: (area / total_area if total_area else 1 / len(components))
        for name, area in component_areas.items()
        if area > 0 or not total_area
    }

    parent_daily = pd.Series(0.0, index=date_index)
    if not selected.empty:
        parent_keys = {name.casefold() for name in parent_names}
        parent_records = selected[
            selected["Field"].astype(str).str.strip().str.casefold().isin(parent_keys)
        ]
        if not parent_records.empty:
            parent_daily = parent_records.groupby("Date")["Irrigation Applied"].sum().reindex(
                date_index, fill_value=0
            )

    result = pd.Series(0.0, index=date_index)
    for field_key, weight in weights.items():
        local_daily = pd.Series(0.0, index=date_index)
        if not selected.empty:
            local_records = selected[
                selected["Field"].astype(str).str.strip().str.casefold() == field_key
            ]
            if not local_records.empty:
                local_daily = local_records.groupby("Date")["Irrigation Applied"].sum().reindex(
                    date_index, fill_value=0
                )
        # A base-name record applies to the whole field; add it to every split.
        if field_key in parent_names:
            component_daily = parent_daily
        else:
            component_daily = parent_daily + local_daily
        result = result + component_daily * weight
    return result


def calculate_soil_moisture_series(daily_weather, irrigation_by_date=None):
    """Apply the shared daily water-balance model and return storage in mm.

    `daily_weather` must be indexed by normalized dates and contain Rainfall
    and Evapotranspiration columns. Irrigation is a date-indexed Series of mm.
    """
    irrigation_by_date = irrigation_by_date if irrigation_by_date is not None else {}
    moisture_mm = INITIAL_SOIL_MOISTURE_MM
    values = []
    for day, weather_row in daily_weather.iterrows():
        rainfall_mm = pd.to_numeric(weather_row.get("Rainfall", 0), errors="coerce")
        evapotranspiration_mm = pd.to_numeric(
            weather_row.get("Evapotranspiration", 0), errors="coerce"
        )
        irrigation_mm = pd.to_numeric(irrigation_by_date.get(day, 0), errors="coerce")
        rainfall_mm = 0.0 if pd.isna(rainfall_mm) else float(rainfall_mm)
        evapotranspiration_mm = 0.0 if pd.isna(evapotranspiration_mm) else float(evapotranspiration_mm)
        irrigation_mm = 0.0 if pd.isna(irrigation_mm) else float(irrigation_mm)
        moisture_mm = max(0.0, min(
            SOIL_WATER_CAPACITY_MM,
            moisture_mm + rainfall_mm + irrigation_mm - evapotranspiration_mm * CROP_ET_FACTOR
        ))
        values.append(moisture_mm)
    return pd.Series(values, index=daily_weather.index, dtype="float64")


def classify_soil_moisture(moisture_mm):
    """Map modeled storage to the existing field-stress bands."""
    if moisture_mm >= 50:
        return "Low"
    if moisture_mm >= 30:
        return "Moderate"
    if moisture_mm >= 10:
        return "High"
    return "Critical"


# ==============================
# 🌱 STRESS CALCULATION (IMPROVED)
# ==============================
def calculate_stress_level(field_name, start_date=None, end_date=None):
    try:
        from datetime import date
        from modules.season import get_active_season
        field_key = str(field_name).strip().casefold()
        weather, irrigation = load_data()
        weather["Date"] = pd.to_datetime(weather["Date"], errors="coerce").dt.normalize()
        irrigation["Date"] = pd.to_datetime(irrigation["Date"], errors="coerce").dt.normalize()
        weather = weather.dropna(subset=["Date"])
        irrigation = irrigation.dropna(subset=["Date"])

        if not start_date or not end_date:
            today = date.today()
            try:
                season_year = int(str(get_active_season() or "").split("/")[0])
            except (TypeError, ValueError):
                season_year = today.year if today.month >= 4 else today.year - 1
            start_date = date(season_year, 4, 1)
            end_date = today
        start = pd.to_datetime(start_date, errors="coerce").normalize()
        end = pd.to_datetime(end_date, errors="coerce").normalize()
        if pd.isna(start) or pd.isna(end) or start > end:
            return "Unknown"

        weather = weather[weather["Date"].between(start, end)]
        if weather.empty:
            return "Unknown"
        daily_weather = weather.groupby("Date")[["Rainfall", "Evapotranspiration"]].sum()
        days = pd.date_range(start, min(end, daily_weather.index.max()), freq="D")
        daily_weather = daily_weather.reindex(days, fill_value=0)
        base_name = base_dg_field_name(field_name)
        family_names = []
        family_areas = {}
        if os.path.exists(GIS_FILE):
            mapped_fields = pd.read_excel(GIS_FILE)
            mapped_fields.columns = mapped_fields.columns.astype(str).str.strip()
            if "Field" in mapped_fields.columns:
                family_rows = mapped_fields[
                    mapped_fields["Field"].map(base_dg_field_name).str.casefold()
                    == base_name.casefold()
                ]
                family_names = family_rows["Field"].dropna().astype(str).str.strip().unique().tolist()
                family_areas = {
                    str(row["Field"]).strip(): pd.to_numeric(row.get("Area (Ha)", 0), errors="coerce")
                    for _, row in family_rows.iterrows()
                }
        if not family_names:
            family_names = irrigation.loc[
                irrigation["Field"].astype(str).map(base_dg_field_name).str.casefold()
                == base_name.casefold(), "Field"
            ].dropna().astype(str).str.strip().unique().tolist()
        family_areas = {
            name: float(area) if pd.notna(area) and area > 0 else 0
            for name, area in family_areas.items()
        }
        family_irrigation = irrigation[irrigation["Date"].between(start, end)]
        irrigation_by_date = aggregate_field_irrigation_by_date(
            family_irrigation, family_names or [field_name], family_areas, daily_weather.index
        )
        moisture = calculate_soil_moisture_series(daily_weather, irrigation_by_date).iloc[-1]
        return classify_soil_moisture(float(moisture))

    except Exception as e:
        print(f"❌ Error calculating stress for {field_name}: {e}")
        traceback.print_exc()
        return "Unknown"


def load_map_data():

    import os
    import json
    import pandas as pd

    from modules.gis_engine.audit import GISAudit


    # -------------------------
    # MAIN FIELDS
    # -------------------------

    fields = []

    if os.path.exists(GIS_FILE):

        df = pd.read_excel(GIS_FILE)

        for _, row in df.iterrows():

            try:

                fields.append({

                    "name": row["Field"],

                    "crop": row["Crop"],

                    "soil": row["Soil"],

                    "area": row["Area (Ha)"],

                    "stress": row.get("Stress Level", "Low"),

                    "geojson": json.loads(row["GeoJSON"])

                })

            except Exception as e:

                print("Field parse error:", e)


    # -------------------------
    # SUB-FIELDS
    # -------------------------

    sub_fields = []

    if os.path.exists("data/sub_fields.xlsx"):

        try:

            sub_df = pd.read_excel("data/sub_fields.xlsx")

            for _, row in sub_df.iterrows():

                try:

                    sub_fields.append({

                        "parent": row["Parent Field"],

                        "name": row["Sub-field"],

                        "area": row["Area (Ha)"],

                        "geojson": json.loads(row["GeoJSON"])

                    })

                except Exception as e:

                    print("Sub-field parse error:", e)

        except Exception as e:

            print("Sub-fields file error:", e)


    # -------------------------
    # QUALITY DATA
    # -------------------------

    quality_data = {}

    try:

        audit = GISAudit.run_audit()

        for item in audit:

            quality_data[item["field"]] = {

                "quality": item["quality"],

                "status": item["status"],

                "warnings": item.get("warnings", [])

            }

    except Exception as e:

        print("GIS quality audit error:", e)

    return fields, sub_fields, quality_data


# ==============================
# 🗺️ ROUTES
# ==============================
@gis_bp.route("/gis/draw")
@role_required(["Manager", "Admin"])
def gis_draw():
    return render_template("gis.html")


@gis_bp.route("/save_polygon", methods=["POST"])
@role_required(["Manager", "Admin"])
def save_polygon():
    try:
        data = request.get_json()

        field_name = data['field'].strip()
        crop = data['crop']
        soil = data['soil']
        geojson = data['geojson']

        area = calculate_area_hectares(geojson)
        stress = calculate_stress_level(field_name)

        if os.path.exists(GIS_FILE):
            df = pd.read_excel(GIS_FILE)
        else:
            df = pd.DataFrame(columns=["Field", "Crop", "Soil", "Area (Ha)", "GeoJSON", "Stress Level"])

        new_row = {
            "Field": field_name,
            "Crop": crop,
            "Soil": soil,
            "Area (Ha)": area,
            "GeoJSON": json.dumps(geojson),
            "Stress Level": stress
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(GIS_FILE, index=False)

        return jsonify({"message": "Polygon saved successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gis_bp.route("/view_fields")
@role_required(["Manager", "Admin"])
def view_fields():
    import os
    import pandas as pd

    if not os.path.exists(GIS_FILE):
        return "No saved fields yet."

    # -------------------------
    # MAIN FIELDS
    # -------------------------
    df = pd.read_excel(GIS_FILE)
    fields = df.to_dict(orient="records")

    # -------------------------
    # SUB-FIELDS (NEW)
    # -------------------------
    sub_fields = []

    if os.path.exists("sub_fields.xlsx"):
        sub_df = pd.read_excel("sub_fields.xlsx")
        sub_fields = sub_df.to_dict(orient="records")

    # -------------------------
    # RENDER
    # -------------------------
    return render_template(
        "view_fields.html",
        fields=fields,
        sub_fields=sub_fields
    )

@gis_bp.route('/add_polygon')
@role_required(["Manager", "Admin"])
def add_polygon():
    return render_template('add_polygon.html')


@gis_bp.route("/delete_polygon", methods=["POST"])
@role_required(["Manager", "Admin"])
def delete_polygon():
    field_name = request.form.get("field")

    if not os.path.exists(GIS_FILE):
        return "GIS file not found."

    df = pd.read_excel(GIS_FILE)
    df = df[df["Field"] != field_name]
    df.to_excel(GIS_FILE, index=False)

    return redirect(url_for("gis.view_fields"))


@gis_bp.route("/edit_polygon/<field_name>", methods=["GET", "POST"])
@role_required(["Manager", "Admin"])
def edit_polygon(field_name):
    import json
    import pandas as pd
    from flask import request, redirect, url_for, render_template, flash, abort

    # Load GIS data from Excel
    try:
        df = pd.read_excel(GIS_FILE)
    except FileNotFoundError:
        abort(500, description="GIS file not found")

    # Fetch field
    field_row = df[df["Field"] == field_name]
    if field_row.empty:
        abort(404, description="Field not found")

    # Convert row to dict for template rendering
    field = field_row.iloc[0].to_dict()

    if request.method == "POST":
        # Get form values
        crop = request.form.get("crop", field.get("Crop", ""))
        soil = request.form.get("soil", field.get("Soil", ""))
        geojson_str = request.form.get("geojson")

        # Update GeoJSON and Area if provided
        if geojson_str:
            try:
                geojson = json.loads(geojson_str)
                area = calculate_area_hectares(geojson)
                df.loc[df["Field"] == field_name, ["Crop", "Soil", "GeoJSON", "Area (Ha)"]] = [
                    crop, soil, json.dumps(geojson), area
                ]
            except (json.JSONDecodeError, ValueError):
                flash("Invalid GeoJSON or area calculation failed", "danger")
                return redirect(request.url)
        else:
            df.loc[df["Field"] == field_name, ["Crop", "Soil"]] = [crop, soil]

        # Save changes
        df.to_excel(GIS_FILE, index=False)
        flash(f"Field '{field_name}' updated successfully!", "success")
        return redirect(url_for("gis.view_fields"))

    # GET request → render template
    return render_template("edit_polygon.html", field=field)


@gis_bp.route("/map_all_fields")
def map_all_fields():

    selected_field = request.args.get("field")

    fields, sub_fields, quality_data = load_map_data()

    return render_template(

        "map_all_fields.html",

        fields=fields,

        sub_fields=sub_fields,

        quality=quality_data,

        selected_field=selected_field

    )

# ==============================
# 🔄 UPDATE STRESS LEVELS
# ==============================
@gis_bp.route('/update_stress_levels', methods=['GET', 'POST'])
def update_stress_levels():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            updated_fields = recalculate_field_stress_levels(
                start_date,
                end_date
            )
            flash(f"✅ Stress levels updated for {updated_fields} fields.", 'success')

        except Exception as e:
            flash(f"⚠️ Error: {e}", 'danger')

        return redirect(url_for('gis.update_stress_levels'))

    return render_template("update_stress_levels.html")


@gis_bp.route('/view_stress_levels')
def view_stress_levels():
    try:
        df = pd.read_excel(GIS_FILE)
        df.columns = df.columns.str.strip()

        if 'Field' not in df.columns or 'Stress Level' not in df.columns:
            flash("❌ Required columns missing.", 'danger')
            return redirect(url_for('dashboard'))

        table_data = df.to_dict(orient='records')
        columns = df.columns.tolist()

    except Exception as e:
        flash(f"⚠️ Error loading data: {e}", 'danger')
        table_data = []
        columns = []

    return render_template('view_stress_levels.html',
                           table_data=table_data,
                           columns=columns)

import pandas as pd
import os

file_path = "data/sub_fields.xlsx"

if not os.path.exists(file_path):
    df = pd.DataFrame(columns=[
        "Parent Field",
        "Sub Field",
        "Area (Ha)",
        "GeoJSON"
    ])
    df.to_excel(file_path, index=False)


import json
import pandas as pd

SUB_FIELDS_FILE = "data/sub_fields.xlsx"

@gis_bp.route('/gis/save_subfield', methods=['POST'])
def save_subfield():
    import pandas as pd
    import json
    import os
    from shapely.geometry import shape, mapping

    parent_field = request.form.get('parent_field')
    sub_field = request.form.get('sub_field')
    geojson_str = request.form.get('geojson')
    manual_area = request.form.get('area')

    # ----------------------------
    # 🔥 VALIDATE INPUT
    # ----------------------------
    if not geojson_str or geojson_str.strip() == "":
        flash("❌ No polygon drawn. Please draw or generate sub-field.", "danger")
        return redirect(url_for('gis.add_subfield', field_name=parent_field))

    try:
        drawn_geo = json.loads(geojson_str)
    except:
        flash("❌ Invalid GeoJSON format.", "danger")
        return redirect(url_for('gis.add_subfield', field_name=parent_field))

    # ----------------------------
    # 🔥 LOAD PARENT FIELD
    # ----------------------------
    df = pd.read_excel('data/field_polygons.xlsx')
    row = df[df['Field'] == parent_field].iloc[0]

    parent_geo = row['GeoJSON']

    if isinstance(parent_geo, str):
        parent_geo = json.loads(parent_geo)

    # 🔥 HANDLE FeatureCollection
    if parent_geo.get("type") == "FeatureCollection":
        parent_geo = parent_geo["features"][0]

    # 🔥 HANDLE Feature
    if parent_geo.get("type") == "Feature":
        parent_geom = shape(parent_geo["geometry"])
    else:
        parent_geom = shape(parent_geo)

    # ----------------------------
    # 🔥 HANDLE DRAWN GEO
    # ----------------------------
    if drawn_geo.get("type") == "FeatureCollection":
        drawn_geo = drawn_geo["features"][0]

    if drawn_geo.get("type") == "Feature":
        drawn_geom = shape(drawn_geo["geometry"])
    else:
        drawn_geom = shape(drawn_geo)

    # ----------------------------
    # 🔥 CLIP TO PARENT
    # ----------------------------
    clipped = parent_geom.intersection(drawn_geom)

    if clipped.is_empty:
        flash("❌ Sub-field is outside parent field.", "danger")
        return redirect(url_for('gis.add_subfield', field_name=parent_field))

    # ----------------------------
    # 🔥 AREA FIX (CORRECT)
    # ----------------------------
    # Convert degrees² → hectares (approx for Malawi latitude)
    area_ha = round(clipped.area * 12365, 2)

    # ----------------------------
    # 🔥 SAVE
    # ----------------------------
    sub_geojson = {
        "type": "Feature",
        "geometry": mapping(clipped)
    }

    new_row = {
        "Parent Field": parent_field,
        "Sub-field": sub_field,
        "Area (Ha)": area_ha,
        "GeoJSON": json.dumps(sub_geojson)
    }

    file_path = 'data/sub_fields.xlsx'

    if os.path.exists(file_path):
        existing = pd.read_excel(file_path)
        new_df = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    else:
        new_df = pd.DataFrame([new_row])

    new_df.to_excel(file_path, index=False)

    flash("✅ Sub-field saved and clipped successfully!", "success")
    return redirect(url_for('gis.view_fields'))


def generate_subfield_name(parent_field):
    import pandas as pd

    df = pd.read_excel("data/sub_fields.xlsx")

    existing = df[df["Parent Field"] == parent_field]

    if existing.empty:
        return parent_field[:-2] + "01"

    last = existing["Sub-field"].iloc[-1]
    number = int(last[-2:]) + 1

    return parent_field[:-2] + str(number).zfill(2)

@gis_bp.route('/gis/add_subfield/<field_name>')
@role_required(["Manager", "Admin"])
def add_subfield(field_name):
    sub_name = generate_subfield_name(field_name)

    if not os.path.exists(GIS_FILE):
        flash("No field data found.", "danger")
        return redirect(url_for('gis.view_fields'))

    df = pd.read_excel(GIS_FILE)

    field_row = df[df["Field"] == field_name]

    if field_row.empty:
        flash("Field not found.", "danger")
        return redirect(url_for('gis.view_fields'))

    field = field_row.iloc[0]

    return render_template(
        "add_subfield.html",
        field_name=field_name,
        sub_name=sub_name,
        parent_geojson=field["GeoJSON"]  # 🔥 THIS WAS MISSING
    )

@gis_bp.route('/gis/auto_split', methods=['POST'])
def auto_split_field():
    import pandas as pd
    import json
    from shapely.geometry import shape, Polygon, mapping
    from shapely.ops import transform
    from pyproj import Transformer

    field_name = request.form['field']
    parts = int(request.form['parts'])

    df = pd.read_excel('data/field_polygons.xlsx')
    row = df[df['Field'] == field_name].iloc[0]

    # ----------------------------
    # SAFE GEOJSON PARSING
    # ----------------------------
    geojson = row['GeoJSON']

    if isinstance(geojson, str):
        geojson = json.loads(geojson)

    if geojson.get("type") == "FeatureCollection":
        geojson = geojson["features"][0]

    if geojson.get("type") == "Feature":
        geometry = geojson.get("geometry", {})
    else:
        geometry = geojson

    if "coordinates" not in geometry:
        flash("Invalid GeoJSON format for this field", "danger")
        return redirect(url_for('gis.view_fields'))

    # ----------------------------
    # MAIN POLYGON
    # ----------------------------
    main_polygon = shape(geometry)

    # ----------------------------
    # PROJECT TO UTM (ACCURATE AREA)
    # Malawi zone = EPSG:32736
    # ----------------------------
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32736", always_xy=True)

    def project(x, y):
        return transformer.transform(x, y)

    projected_main = transform(project, main_polygon)

    # ----------------------------
    # BOUNDING BOX SPLIT
    # ----------------------------
    minx, miny, maxx, maxy = main_polygon.bounds
    width = (maxx - minx) / parts

    sub_fields = []

    # ----------------------------
    # CREATE + CLIP SUB-FIELDS
    # ----------------------------
    for i in range(parts):
        sub_minx = minx + i * width
        sub_maxx = sub_minx + width

        rect = Polygon([
            (sub_minx, miny),
            (sub_maxx, miny),
            (sub_maxx, maxy),
            (sub_minx, maxy),
            (sub_minx, miny)
        ])

        clipped = main_polygon.intersection(rect)

        if clipped.is_empty:
            continue

        # 🔥 PROJECT CLIPPED POLYGON FOR ACCURATE AREA
        projected_clip = transform(project, clipped)

        area_ha = projected_clip.area / 10000

        sub_geojson = {
            "type": "Feature",
            "geometry": mapping(clipped)
        }

        sub_name = f"{field_name}{str(i+1).zfill(2)}"

        sub_fields.append({
            "Parent Field": field_name,
            "Sub-field": sub_name,
            "GeoJSON": json.dumps(sub_geojson),
            "Area (Ha)": round(area_ha, 2)
        })

    # ----------------------------
    # SAVE TO EXCEL
    # ----------------------------
    sub_df = pd.DataFrame(sub_fields)

    try:
        existing = pd.read_excel('data/sub_fields.xlsx')
        sub_df = pd.concat([existing, sub_df], ignore_index=True)
    except:
        pass

    sub_df.to_excel('data/sub_fields.xlsx', index=False)

    flash(f"{len(sub_fields)} clipped sub-fields created successfully!", "success")
    return redirect(url_for('gis.view_fields'))

@gis_bp.route('/gis/auto_split_manual', methods=['POST'])
def auto_split_manual():
    import pandas as pd
    import json
    from shapely.geometry import shape, Polygon, mapping
    from shapely.ops import transform
    from pyproj import Transformer

    field_name = request.form['field']
    target_area = float(request.form['area'])  # 🔥 manual ha input

    df = pd.read_excel('data/field_polygons.xlsx')
    row = df[df['Field'] == field_name].iloc[0]

    # ----------------------------
    # GEOJSON PARSE
    # ----------------------------
    geojson = row['GeoJSON']
    if isinstance(geojson, str):
        geojson = json.loads(geojson)

    if geojson.get("type") == "Feature":
        geometry = geojson["geometry"]
    else:
        geometry = geojson

    main_polygon = shape(geometry)

    # ----------------------------
    # PROJECT TO UTM
    # ----------------------------
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32736", always_xy=True)

    def project(x, y):
        return transformer.transform(x, y)

    projected_main = transform(project, main_polygon)

    total_area = projected_main.area / 10000

    # ----------------------------
    # SWEEP SPLITTING
    # ----------------------------
    minx, miny, maxx, maxy = main_polygon.bounds

    step = (maxx - minx) / 100  # small step for slicing
    current_x = minx

    sub_fields = []
    accumulated = None
    part_index = 1

    while current_x < maxx:

        slice_rect = Polygon([
            (current_x, miny),
            (current_x + step, miny),
            (current_x + step, maxy),
            (current_x, maxy),
            (current_x, miny)
        ])

        piece = main_polygon.intersection(slice_rect)

        if piece.is_empty:
            current_x += step
            continue

        if accumulated is None:
            accumulated = piece
        else:
            accumulated = accumulated.union(piece)

        # 🔥 Calculate area
        proj_piece = transform(project, accumulated)
        area_ha = proj_piece.area / 10000

        # 🔥 If reached target → save
        if area_ha >= target_area:
            sub_geojson = {
                "type": "Feature",
                "geometry": mapping(accumulated)
            }

            sub_name = f"{field_name}{str(part_index).zfill(2)}"

            sub_fields.append({
                "Parent Field": field_name,
                "Sub-field": sub_name,
                "GeoJSON": json.dumps(sub_geojson),
                "Area (Ha)": round(area_ha, 2)
            })

            part_index += 1
            accumulated = None  # reset

        current_x += step

    # ----------------------------
    # LAST REMAINDER
    # ----------------------------
    if accumulated and not accumulated.is_empty:
        proj_piece = transform(project, accumulated)
        area_ha = proj_piece.area / 10000

        sub_geojson = {
            "type": "Feature",
            "geometry": mapping(accumulated)
        }

        sub_name = f"{field_name}{str(part_index).zfill(2)}"

        sub_fields.append({
            "Parent Field": field_name,
            "Sub-field": sub_name,
            "GeoJSON": json.dumps(sub_geojson),
            "Area (Ha)": round(area_ha, 2)
        })

    # ----------------------------
    # SAVE
    # ----------------------------
    sub_df = pd.DataFrame(sub_fields)

    try:
        existing = pd.read_excel('data/sub_fields.xlsx')
        sub_df = pd.concat([existing, sub_df], ignore_index=True)
    except:
        pass

    sub_df.to_excel('data/sub_fields.xlsx', index=False)

    flash(f"{len(sub_fields)} sub-fields (~{target_area} ha) created!", "success")
    return redirect(url_for('gis.view_fields'))

def load_field_geojson(field_name):

    import pandas as pd
    import json
    import os


    file_path = "data/field_polygons.xlsx"


    if not os.path.exists(file_path):
        return None


    df = pd.read_excel(file_path)


    row = df[
        df["Field"] == field_name
    ]


    if row.empty:
        return None


    geojson = row.iloc[0]["GeoJSON"]


    try:

        data = json.loads(geojson)

        return data


    except Exception as e:

        print(
            "GeoJSON error:",
            e
        )

        return None


@gis_bp.route("/api/gis-summary")
def gis_summary():

    from modules.gis_engine.dashboard import GISDashboard

    summary = GISDashboard.get_summary()

    return jsonify(summary)

@gis_bp.route("/api/gis-audit")
def gis_audit():

    from modules.gis_engine.audit import GISAudit

    results = GISAudit.run_audit()

    return jsonify(results)

@gis_bp.route("/gis-review")
def gis_review():

    from modules.gis_engine.audit import GISAudit

    results = GISAudit.run_audit()


    review_fields = [
        field for field in results
        if field["status"] != "OK"
    ]


    return render_template(
        "gis_review.html",
        fields=review_fields
    )

@gis_bp.route("/gis-quality-map")
def gis_quality_map():

    return render_template(
        "gis_quality_map.html"
    )

@gis_bp.route("/api/gis-quality-data")
def gis_quality_data():

    from modules.gis_engine.audit import GISAudit

    audit = GISAudit.run_audit()


    results=[]


    for field in audit:


        results.append({

            "field":
                field["field"],

            "quality":
                field["quality"],

            "status":
                field["status"],

            "area":
                field["gis_area"],

            "geojson":
                load_field_geojson(
                    field["field"]
                )

        })


    return jsonify(results)

@gis_bp.route("/gis-dashboard")
@role_required(["Admin", "Manager"])
def gis_dashboard():

    return render_template(
        "gis_dashboard.html"
    )



@gis_bp.route("/api/gis-dashboard")
def gis_dashboard_api():

    from modules.gis_engine.dashboard import GISDashboard

    return jsonify(
        GISDashboard.get_summary()
    )

@gis_bp.route("/api/map-fields")
def map_fields():

    fields, sub_fields, quality_data = load_map_data()

    return jsonify({

        "fields": fields,

        "sub_fields": sub_fields,

        "quality": quality_data

    })

@gis_bp.route("/api/field360/<field_name>")
def field360_api(field_name):
    result = build_field360(field_name)

    result = make_json_safe(result)

    return jsonify(result)

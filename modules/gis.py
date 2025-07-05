from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import pandas as pd
import os
import json
import geopandas as gpd
from shapely.geometry import shape
from modules.utils import role_required

GIS_FILE = 'data/field_polygons.xlsx'
WEATHER_FILE = 'data/weather_data.xlsx'
IRRIGATION_FILE = 'data/irrigation_records.xlsx'

gis_bp = Blueprint('gis', __name__)

def calculate_area_hectares(geojson):
    geom = shape(geojson['features'][0]['geometry'])
    gdf = gpd.GeoDataFrame(index=[0], geometry=[geom], crs="EPSG:4326")
    gdf = gdf.to_crs(epsg=3857)
    area_m2 = gdf['geometry'].area[0]
    return round(area_m2 / 10000, 2)


# File paths (update as needed)
WEATHER_FILE = 'data/weather_data.xlsx'
IRRIGATION_FILE = 'data/irrigation_records.xlsx'

import traceback

def calculate_stress_level(field_name, start_date=None, end_date=None):
    try:
        print(f"➡️ Calculating stress for field: {field_name}")

        weather = pd.read_excel(WEATHER_FILE)
        irrigation = pd.read_excel(IRRIGATION_FILE)

        weather['Date'] = pd.to_datetime(weather['Date'])
        irrigation['Date'] = pd.to_datetime(irrigation['Date'])

        if start_date and end_date:
            weather = weather[(weather['Date'] >= start_date) & (weather['Date'] <= end_date)]
            irrigation = irrigation[(irrigation['Date'] >= start_date) & (irrigation['Date'] <= end_date)]

        rainfall = weather['Rainfall'].sum()
        et = weather['Evapotranspiration'].sum()

        irrigation_total = irrigation[irrigation['Field'] == field_name]['Irrigation Applied'].sum()

        print(f"🌧️ Rainfall: {rainfall}, ☀️ ET: {et}, 💧 Irrigation: {irrigation_total}")

        water_balance = rainfall + irrigation_total - et

        if water_balance >= 50:
            return "Low"
        elif 30 <= water_balance < 50:
            return "Moderate"
        elif 10 <= water_balance < 30:
            return "High"
        else:
            return "Critical"

    except Exception as e:
        print(f"❌ Error calculating stress for {field_name}: {e}")
        traceback.print_exc()
        return "Unknown"


@gis_bp.route("/gis/draw")
@role_required(["Manager", "Admin"])
def gis_draw():
    return render_template("gis.html")

@gis_bp.route("/save_polygon", methods=["POST"])
@role_required(["Manager", "Admin"])
def save_polygon():
    try:
        data = request.get_json()
        field_name = data['field']
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
    if not os.path.exists(GIS_FILE):
        return "No saved fields yet."

    df = pd.read_excel(GIS_FILE)
    return render_template("view_fields.html", fields=df.to_dict(orient="records"))

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
    if not os.path.exists(GIS_FILE):
        return "GIS file not found."

    df = pd.read_excel(GIS_FILE)
    record = df[df["Field"] == field_name]

    if request.method == "POST":
        crop = request.form.get("crop")
        soil = request.form.get("soil")
        df.loc[df["Field"] == field_name, ["Crop", "Soil"]] = [crop, soil]
        df.to_excel(GIS_FILE, index=False)
        return redirect(url_for("gis.view_fields"))

    if record.empty:
        return "Field not found."

    return render_template("edit_polygon.html", field=record.iloc[0].to_dict())

@gis_bp.route('/map_all_fields')
def map_all_fields():
    if not os.path.exists(GIS_FILE):
        return "No saved fields to display."

    df = pd.read_excel(GIS_FILE)
    fields = []

    for _, row in df.iterrows():
        fields.append({
            "name": row["Field"],
            "crop": row["Crop"],
            "soil": row["Soil"],
            "area": row["Area (Ha)"],
            "stress": row.get("Stress Level", "Low"),
            "geojson": json.loads(row["GeoJSON"])
        })

    return render_template('map_all_fields.html', fields=fields)

import pandas as pd

# Your stress level function must be already defined
# from previous code: calculate_stress_level(...)

FIELD_POLYGONS_FILE = 'data/field_polygons.xlsx'

def update_field_stress_levels(start_date=None, end_date=None):
    try:
        # Load field polygons file
        df = pd.read_excel(FIELD_POLYGONS_FILE)

        # Normalize column headers
        df.columns = df.columns.str.strip()

        # Ensure there's a 'Field' column
        if 'Field' not in df.columns:
            raise ValueError("The Excel file must contain a 'Field' column.")

        # Create/update Stress Level column
        stress_levels = []
        for field in df['Field']:
            level = calculate_stress_level(field, start_date, end_date)
            stress_levels.append(level)

        df['Stress Level'] = stress_levels

        # Save back to the same Excel file (or new one if you prefer)
        df.to_excel(FIELD_POLYGONS_FILE, index=False)
        print(f"✅ Stress levels updated in '{FIELD_POLYGONS_FILE}'")

    except Exception as e:
        print(f"❌ Failed to update stress levels: {e}")

from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os

FIELD_POLYGONS_FILE = 'data/field_polygons.xlsx'

@gis_bp.route('/update_stress_levels', methods=['GET', 'POST'])
def update_stress_levels():
    message = ""
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            df = pd.read_excel(FIELD_POLYGONS_FILE)
            df.columns = df.columns.str.strip()

            if 'Field' not in df.columns:
                flash("❌ 'Field' column not found in field_polygons.xlsx", 'danger')
                return redirect(url_for('gis.update_stress_levels'))

            stress_levels = []
            for field in df['Field']:
                level = calculate_stress_level(field, start_date, end_date)
                stress_levels.append(level)

            df['Stress Level'] = stress_levels
            df.to_excel(FIELD_POLYGONS_FILE, index=False)

            flash(f"✅ Stress levels updated for {len(df)} fields.", 'success')
            return redirect(url_for('gis.update_stress_levels'))

        except Exception as e:
            flash(f"⚠️ Error: {e}", 'danger')

    return render_template("update_stress_levels.html")


@gis_bp.route('/view_stress_levels')
def view_stress_levels():
    try:
        df = pd.read_excel('data/field_polygons.xlsx')
        df.columns = df.columns.str.strip()

        if 'Field' not in df.columns or 'Stress Level' not in df.columns:
            flash("❌ Required columns 'Field' and 'Stress Level' not found.", 'danger')
            return redirect(url_for('dashboard'))

        table_data = df.to_dict(orient='records')
        columns = df.columns.tolist()

    except Exception as e:
        flash(f"⚠️ Error loading stress level data: {e}", 'danger')
        table_data = []
        columns = []

    return render_template('view_stress_levels.html',
                           table_data=table_data,
                           columns=columns)

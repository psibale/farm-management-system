from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
import os
import json
import geopandas as gpd
from shapely.geometry import shape
from modules.utils import role_required
import traceback

gis_bp = Blueprint('gis', __name__)

# File paths
GIS_FILE = 'data/field_polygons.xlsx'
WEATHER_FILE = 'data/weather_data.xlsx'
IRRIGATION_FILE = 'data/irrigation_records.xlsx'


# ==============================
# 🌍 AREA CALCULATION
# ==============================
def calculate_area_hectares(geojson):
    geom = shape(geojson['features'][0]['geometry'])
    gdf = gpd.GeoDataFrame(index=[0], geometry=[geom], crs="EPSG:4326")
    gdf = gdf.to_crs(epsg=3857)
    area_m2 = gdf['geometry'].area[0]
    return round(area_m2 / 10000, 2)


# ==============================
# 📊 LOAD DATA (PERFORMANCE FIX)
# ==============================
def load_data():
    weather = pd.read_excel(WEATHER_FILE)
    irrigation = pd.read_excel(IRRIGATION_FILE)

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


# ==============================
# 🌱 STRESS CALCULATION (IMPROVED)
# ==============================
def calculate_stress_level(field_name, start_date=None, end_date=None):
    try:
        print(f"➡️ Calculating stress for field: {field_name}")

        # Normalize field name
        field_name = str(field_name).strip().lower()

        weather, irrigation = load_data()

        # Convert dates if provided
        if start_date and end_date:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)

            weather = weather[(weather['Date'] >= start_date) & (weather['Date'] <= end_date)]
            irrigation = irrigation[(irrigation['Date'] >= start_date) & (irrigation['Date'] <= end_date)]

        rainfall = weather['Rainfall'].sum()
        et = weather['Evapotranspiration'].sum()

        irrigation_total = irrigation[irrigation['Field'] == field_name]['Irrigation Applied'].sum()

        print(f"🌧️ Rainfall: {rainfall}, ☀️ ET: {et}, 💧 Irrigation: {irrigation_total}")

        # 🌾 Crop factor for sugarcane
        CROP_FACTOR = 1.2
        adjusted_et = et * CROP_FACTOR

        water_balance = rainfall + irrigation_total - adjusted_et

        # Optional: stress %
        stress_percent = (water_balance / adjusted_et) * 100 if adjusted_et > 0 else 0
        print(f"📊 Stress %: {round(stress_percent, 2)}")

        # Stress classification
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


# ==============================
# 🔄 UPDATE STRESS LEVELS
# ==============================
@gis_bp.route('/update_stress_levels', methods=['GET', 'POST'])
def update_stress_levels():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            df = pd.read_excel(GIS_FILE)
            df.columns = df.columns.str.strip()

            if 'Field' not in df.columns:
                flash("❌ 'Field' column not found.", 'danger')
                return redirect(url_for('gis.update_stress_levels'))

            stress_levels = []
            for field in df['Field']:
                level = calculate_stress_level(field, start_date, end_date)
                stress_levels.append(level)

            df['Stress Level'] = stress_levels
            df.to_excel(GIS_FILE, index=False)

            flash(f"✅ Stress levels updated for {len(df)} fields.", 'success')

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
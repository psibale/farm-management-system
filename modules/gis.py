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

def calculate_stress_level(field_name, start_date=None, end_date=None):
    try:
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

        water_balance = rainfall + irrigation_total - et

        if water_balance >= 50:
            return "Low"
        elif 30 <= water_balance < 50:
            return "Moderate"
        elif 10 <= water_balance < 30:
            return "High"
        else:
            return "Critical"
    except:
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
        field_name = data['field_name']
        crop = data['crop']
        soil = data['soil']
        geojson = data['geojson']

        area = calculate_area_hectares(geojson)
        stress = calculate_stress_level(field_name)

        if os.path.exists(GIS_FILE):
            df = pd.read_excel(GIS_FILE)
        else:
            df = pd.DataFrame(columns=["Field Name", "Crop", "Soil", "Area (Ha)", "GeoJSON", "Stress Level"])

        new_row = {
            "Field Name": field_name,
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
    field_name = request.form.get("field_name")
    if not os.path.exists(GIS_FILE):
        return "GIS file not found."

    df = pd.read_excel(GIS_FILE)
    df = df[df["Field Name"] != field_name]
    df.to_excel(GIS_FILE, index=False)
    return redirect(url_for("gis.view_fields"))

@gis_bp.route("/edit_polygon/<field_name>", methods=["GET", "POST"])
@role_required(["Manager", "Admin"])
def edit_polygon(field_name):
    if not os.path.exists(GIS_FILE):
        return "GIS file not found."

    df = pd.read_excel(GIS_FILE)
    record = df[df["Field Name"] == field_name]

    if request.method == "POST":
        crop = request.form.get("crop")
        soil = request.form.get("soil")
        df.loc[df["Field Name"] == field_name, ["Crop", "Soil"]] = [crop, soil]
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
            "name": row["Field Name"],
            "crop": row["Crop"],
            "soil": row["Soil"],
            "area": row["Area (Ha)"],
            "stress": row.get("Stress Level", "Low"),
            "geojson": json.loads(row["GeoJSON"])
        })

    return render_template('map_all_fields.html', fields=fields)


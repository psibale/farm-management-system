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
SUB_FIELDS_FILE = "data/sub_fields.xlsx"

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


@gis_bp.route('/map_all_fields')
def map_all_fields():
    import os
    import json
    import pandas as pd

    # -------------------------
    # MAIN FIELDS
    # -------------------------
    if not os.path.exists(GIS_FILE):
        return "No saved fields to display."

    df = pd.read_excel(GIS_FILE)
    fields = []

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
    # SUB-FIELDS (NEW FIX)
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
    # RENDER (IMPORTANT FIX)
    # -------------------------
    return render_template(
        'map_all_fields.html',
        fields=fields,
        sub_fields=sub_fields   # 🔥 FIX: prevents Undefined error
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
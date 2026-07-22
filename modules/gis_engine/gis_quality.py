"""
=========================================================
Farm Management System
GIS Quality Engine
=========================================================

Provides GIS quality information for the
DCGL GIS Dashboard and Field360.

Author:
    Peter Sibale

Version:
    1.0
=========================================================
"""

import json
import os
import pandas as pd

from .validator import GISValidator
from .calculations import Coordinate

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
# GEOJSON → COORDINATES
# -------------------------------------------------

def geojson_to_points(geojson):

    import json

    if isinstance(geojson, str):

        geojson = json.loads(geojson)

    # -----------------------------------------
    # FeatureCollection
    # -----------------------------------------

    if geojson.get("type") == "FeatureCollection":

        coordinates = geojson["features"][0]["geometry"]["coordinates"][0]

    # -----------------------------------------
    # Feature
    # -----------------------------------------

    elif geojson.get("type") == "Feature":

        coordinates = geojson["geometry"]["coordinates"][0]

    # -----------------------------------------
    # Polygon
    # -----------------------------------------

    elif geojson.get("type") == "Polygon":

        coordinates = geojson["coordinates"][0]

    else:

        raise ValueError(
            f"Unsupported GeoJSON type: {geojson.get('type')}"
        )

    points = []

    for lon, lat in coordinates:

        points.append(

            Coordinate(

                latitude=lat,

                longitude=lon

            )

        )

    return points


# -------------------------------------------------
# FIELD GIS QUALITY
# -------------------------------------------------

def get_field_quality(field_name):

    polygons = load_excel("field_polygons.xlsx")

    if polygons.empty:

        return None

    row = polygons[polygons["Field"] == field_name]

    if row.empty:

        return None

    geojson = row.iloc[0]["GeoJSON"]

    points = geojson_to_points(geojson)

    report = GISValidator.create_report(points)

    return {

        "field": field_name,

        "quality": report.quality_score,

        "valid": report.valid,

        "area": round(report.field_area_ha, 2),

        "perimeter": round(report.perimeter_m, 2),

        "compactness": round(report.compactness, 2),

        "warnings": report.warnings,

        "errors": report.errors

    }


# -------------------------------------------------
# FARM SUMMARY
# -------------------------------------------------

def get_farm_quality_summary():

    polygons = load_excel("field_polygons.xlsx")

    if polygons.empty:

        return {}

    total = 0

    valid = 0

    review = 0

    invalid = 0

    total_quality = 0

    fields = []

    for _, row in polygons.iterrows():

        result = get_field_quality(row["Field"])

        if not result:
            continue

        total += 1

        total_quality += result["quality"]

        if result["quality"] >= 100:

            valid += 1

        elif result["quality"] >= 90:

            review += 1

        else:

            invalid += 1

        fields.append(result)

    average = 0

    if total:

        average = round(total_quality / total, 1)

    return {

        "total_fields": total,

        "excellent": valid,

        "review": review,

        "invalid": invalid,

        "average_quality": average,

        "fields": fields

    }
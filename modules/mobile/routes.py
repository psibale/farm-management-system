from flask import Blueprint, render_template
from flask import Blueprint, request, jsonify
import pandas as pd
import json
import os

mobile_bp = Blueprint(
    "mobile",
    __name__,
    template_folder="../../templates/mobile"
)



@mobile_bp.route("/")
def mobile_home():

    return render_template("mobile/index.html")

@mobile_bp.route("/")
def home():

    return render_template("mobile/mobile_home.html")


@mobile_bp.route("/survey")
def survey():

    return render_template("mobile/survey.html")


@mobile_bp.route("/inspection")
def inspection():

    return render_template("mobile/inspection.html")


@mobile_bp.route("/sync")
def sync():

    return render_template("mobile/sync.html")

@mobile_bp.route("/save_survey", methods=["POST"])
def save_survey():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    geojson = data.get("geojson")

    field = data.get("field", "NEW_FIELD")

    area = data.get("area", 0)

    crop = data.get("crop", "")

    soil = data.get("soil", "")

    excel_file = os.path.join(
        "data",
        "field_polygons.xlsx"
    )

    if os.path.exists(excel_file):

        df = pd.read_excel(excel_file)

    else:

        df = pd.DataFrame(columns=[
            "Field",
            "Crop",
            "Soil",
            "Area (Ha)",
            "GeoJSON",
            "Stress Level"
        ])

    df.loc[len(df)] = [

        field,

        crop,

        soil,

        area,

        json.dumps(geojson),

        "Low"

    ]

    df.to_excel(excel_file, index=False)

    return jsonify({

        "success": True,

        "message": "Survey saved."

    })


@mobile_bp.route("/survey_details")
def survey_details():

    return render_template("mobile/survey_details.html")





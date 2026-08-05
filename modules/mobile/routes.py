from flask import Blueprint, request, jsonify
from flask import Blueprint, render_template, session
from config import DATA_FOLDER
from modules.mobile.survey_manager import SurveyManager
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


# ==========================================================
# SURVEY DATA API
# ==========================================================

@mobile_bp.route("/survey_data")
def survey_data():

    survey = SurveyManager(DATA_FOLDER)

    return jsonify({

        "system": survey.system_info(),

        "survey_types": [

            "Main Field",

            "Sub-field",

            "Update Boundary"

        ],

        "parent_fields": survey.get_parent_fields(),

        "total_fields": survey.total_fields(),

        "total_subfields": survey.total_subfields(),

        "season": "2026/27",

        "surveyor": session.get("username", "Unknown")

    })

# ==========================================================
# NEXT AVAILABLE SUB-FIELD
# ==========================================================

@mobile_bp.route("/next_subfield/<parent>")
def next_subfield(parent):

    survey = SurveyManager(DATA_FOLDER)

    next_name = survey.generate_subfield_name(parent)

    stats = survey.remaining_area(parent)

    return jsonify({

        "parent": parent,

        "next": next_name,

        "existing_subfields": len(
            survey.get_subfields(parent)
        ),

        "parent_area": stats["parent_area"],

        "surveyed_area": stats["surveyed_area"],

        "remaining_area": stats["remaining_area"]

    })
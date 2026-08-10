from flask import Blueprint, request, jsonify, render_template, session

from config import DATA_FOLDER
from modules.mobile.survey_manager import SurveyManager

import pandas as pd
import json
import os


# ==========================================================
# SURVEY MANAGER
# ==========================================================

survey_manager = SurveyManager(DATA_FOLDER)


# ==========================================================
# MOBILE BLUEPRINT
# ==========================================================

mobile_bp = Blueprint(
    "mobile",
    __name__,
    template_folder="../../templates/mobile"
)


# ==========================================================
# MOBILE HOME
# ==========================================================

@mobile_bp.route("/")
def mobile_home():

    return render_template("mobile/index.html")


# ==========================================================
# MOBILE HOME / MAIN
# ==========================================================

@mobile_bp.route("/home")
def home():

    return render_template("mobile/mobile_home.html")


# ==========================================================
# SURVEY
# ==========================================================

@mobile_bp.route("/survey")
def survey():

    return render_template("mobile/survey.html")


# ==========================================================
# INSPECTION
# ==========================================================

@mobile_bp.route("/inspection")
def inspection():

    return render_template("mobile/inspection.html")


# ==========================================================
# SYNC
# ==========================================================

@mobile_bp.route("/sync")
def sync():

    return render_template("mobile/sync.html")


# ==========================================================
# SURVEY DETAILS
# ==========================================================

@mobile_bp.route("/survey_details")
def survey_details():

    return render_template(
        "mobile/survey_details.html"
    )


# ==========================================================
# SURVEY REVIEW
# ==========================================================

@mobile_bp.route("/survey_review")
def survey_review():

    return render_template(
        "mobile/survey_review.html"
    )


# ==========================================================
# SAVE SURVEY
# ==========================================================

@mobile_bp.route("/save_survey", methods=["POST"])
def save_survey():

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "message": "No survey data received."

            }), 400


        print("=" * 60)
        print("SAVE SURVEY CALLED")
        print("SURVEY TYPE:", data.get("survey_type"))
        print("FIELD:", data.get("field"))
        print("PARENT:", data.get("parent"))
        print("AREA:", data.get("area"))
        print("=" * 60)


        survey_manager.save_survey(data)

        # Refresh manager so newly saved Excel data
        # is immediately available to the next request.

        survey_manager.refresh()


        return jsonify({

            "success": True,

            "message": "Survey saved successfully."

        })


    except Exception as e:

        print("=" * 60)
        print("SAVE SURVEY ERROR")
        print(e)
        print("=" * 60)


        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


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

        "parent_fields":
            survey.get_parent_fields(),

        "total_fields":
            survey.total_fields(),

        "total_subfields":
            survey.total_subfields(),

        "season":
            "2026/27",

        "surveyor":
            session.get(
                "username",
                "Unknown"
            )

    })


# ==========================================================
# NEXT AVAILABLE SUB-FIELD
# ==========================================================

@mobile_bp.route("/next_subfield/<parent>")
def next_subfield(parent):

    survey = SurveyManager(DATA_FOLDER)


    next_name = \
        survey.generate_subfield_name(parent)


    stats = \
        survey.remaining_area(parent)


    return jsonify({

        "success": True,

        "parent": parent,

        "next": next_name,

        "existing_subfields":
            len(
                survey.get_subfields(parent)
            ),

        "parent_area":
            stats["parent_area"],

        "surveyed_area":
            stats["surveyed_area"],

        "remaining_area":
            stats["remaining_area"]

    })


# ==========================================================
# PARENT AREA
# ==========================================================

@mobile_bp.route("/parent_area/<parent>")
def parent_area(parent):

    try:

        survey = SurveyManager(DATA_FOLDER)


        result = \
            survey.remaining_area(parent)


        return jsonify({

            "success": True,

            "parent": parent,

            "parent_area":
                result["parent_area"],

            "surveyed_area":
                result["surveyed_area"],

            "remaining_area":
                result["remaining_area"]

        })


    except Exception as e:

        print("=" * 60)
        print("PARENT AREA ERROR")
        print(e)
        print("=" * 60)


        return jsonify({

            "success": False,

            "message": str(e)

        }), 500
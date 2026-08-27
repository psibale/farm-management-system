from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
    current_app,
    Response
)

from functools import wraps

from config import DATA_FOLDER
from modules.mobile.survey_manager import SurveyManager

import pandas as pd
import json
import os


# ==========================================================
# FIELDMATE LOGIN PROTECTION
# ==========================================================

def fieldmate_login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        # --------------------------------------------------
        # CHECK EXISTING FARM MANAGEMENT LOGIN
        # --------------------------------------------------

        if "username" not in session:

            return redirect(
                url_for("home")
            )

        return view(*args, **kwargs)

    return wrapped_view


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
@fieldmate_login_required
def mobile_home():

    return render_template(
        "mobile/index.html"
    )


# ==========================================================
# MOBILE HOME / MAIN
# ==========================================================

@mobile_bp.route("/home")
@fieldmate_login_required
def home():

    return render_template(
        "mobile/mobile_home.html"
    )


# ==========================================================
# SURVEY
# ==========================================================

@mobile_bp.route("/survey")
@fieldmate_login_required
def survey():

    return render_template(
        "mobile/survey.html"
    )


# ==========================================================
# INSPECTION
# ==========================================================

@mobile_bp.route("/inspection")
@fieldmate_login_required
def inspection():

    return render_template(
        "mobile/inspection.html"
    )


# ==========================================================
# SYNC
# ==========================================================

@mobile_bp.route("/sync")
@fieldmate_login_required
def sync():

    return render_template(
        "mobile/sync.html"
    )


# ==========================================================
# SURVEY DETAILS
# ==========================================================

@mobile_bp.route("/survey_details")
@fieldmate_login_required
def survey_details():

    return render_template(
        "mobile/survey_details.html"
    )


# ==========================================================
# SURVEY REVIEW
# ==========================================================

@mobile_bp.route("/survey_review")
@fieldmate_login_required
def survey_review():

    return render_template(
        "mobile/survey_review.html"
    )


# ==========================================================
# SAVE SURVEY
# ==========================================================

@mobile_bp.route(
    "/save_survey",
    methods=["POST"]
)
@fieldmate_login_required
def save_survey():

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "message":
                    "No survey data received."

            }), 400


        # ==================================================
        # GET LOGGED-IN USER
        # ==================================================

        username = session.get(
            "username",
            "Unknown"
        )


        # ==================================================
        # FORCE SERVER USERNAME
        #
        # Do not trust the username sent by the phone.
        # The Flask session is authoritative.
        # ==================================================

        data["surveyor"] = username


        # ==================================================
        # DEBUG INFORMATION
        # ==================================================

        print("=" * 60)
        print("MOBILE SURVEY SAVE")
        print("=" * 60)

        print(
            "LOGGED-IN USER:",
            username
        )

        print(
            "SURVEY TYPE:",
            data.get("survey_type")
        )

        print(
            "FIELD:",
            data.get("field")
        )

        print(
            "PARENT:",
            data.get("parent")
        )

        print(
            "AREA:",
            data.get("area")
        )

        print(
            "SURVEYOR:",
            data.get("surveyor")
        )

        print(
            "SURVEY ID:",
            data.get("survey_id")
        )

        print("=" * 60)


        # ==================================================
        # SAVE SURVEY
        # ==================================================

        result = survey_manager.save_survey(
            data
        )


        print(
            "SAVE RESULT:"
        )

        print(result)


        # ==================================================
        # REFRESH MANAGER
        # ==================================================

        survey_manager.refresh()


        # ==================================================
        # SUCCESS
        # ==================================================

        return jsonify({

            "success": True,

            "message":
                "Survey saved successfully.",

            "surveyor":
                username

        })


    except Exception as e:

        print("=" * 60)
        print("SAVE SURVEY ERROR")
        print(e)
        print("=" * 60)


        return jsonify({

            "success": False,

            "message":
                str(e)

        }), 500


# ==========================================================
# SURVEY DATA API
# ==========================================================

@mobile_bp.route("/survey_data")
@fieldmate_login_required
def survey_data():

    survey = SurveyManager(
        DATA_FOLDER
    )

    return jsonify({

        "system":
            survey.system_info(),

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

@mobile_bp.route(
    "/next_subfield/<parent>"
)
def next_subfield(parent):

    survey = SurveyManager(
        DATA_FOLDER
    )


    next_name = \
        survey.generate_subfield_name(
            parent
        )


    stats = \
        survey.remaining_area(
            parent
        )


    return jsonify({

        "success": True,

        "parent": parent,

        "next": next_name,

        "existing_subfields":
            len(
                survey.get_subfields(
                    parent
                )
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

@mobile_bp.route(
    "/parent_area/<parent>"
)
def parent_area(parent):

    try:

        survey = SurveyManager(
            DATA_FOLDER
        )


        result = \
            survey.remaining_area(
                parent
            )


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

            "message":
                str(e)

        }), 500


# ==========================================================
# DCGL FIELDMATE
# SERVICE WORKER
# ==========================================================

@mobile_bp.route(
    "/service-worker.js"
)
def service_worker():

    # ------------------------------------------------------
    # SERVICE WORKER FILE
    #
    # Physical file remains:
    #
    # static/mobile/service-worker.js
    #
    # But it is exposed to the browser as:
    #
    # /mobile/service-worker.js
    #
    # This is important because the Service Worker must
    # control the /mobile/ application.
    # ------------------------------------------------------

    sw_path = os.path.join(

        current_app.static_folder,

        "mobile",

        "service-worker.js"

    )


    # ------------------------------------------------------
    # CHECK FILE
    # ------------------------------------------------------

    if not os.path.exists(sw_path):

        print(
            "SERVICE WORKER NOT FOUND:",
            sw_path
        )

        return (
            "Service Worker not found.",
            404
        )


    # ------------------------------------------------------
    # READ SERVICE WORKER
    # ------------------------------------------------------

    try:

        with open(
            sw_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()


    except Exception as e:

        print(
            "SERVICE WORKER READ ERROR:",
            e
        )

        return (
            "Unable to read Service Worker.",
            500
        )


    # ------------------------------------------------------
    # RETURN JAVASCRIPT
    # ------------------------------------------------------

    response = Response(

        content,

        mimetype="application/javascript"

    )


    # ------------------------------------------------------
    # IMPORTANT
    #
    # Normally a Service Worker can only control URLs
    # underneath its own directory.
    #
    # Because the physical file is in:
    #
    # /static/mobile/
    #
    # but we want it to control:
    #
    # /mobile/
    #
    # this header expands the allowed scope.
    # ------------------------------------------------------

    response.headers[
        "Service-Worker-Allowed"
    ] = "/mobile/"


    # ------------------------------------------------------
    # DO NOT CACHE DURING DEVELOPMENT
    # ------------------------------------------------------

    response.headers[
        "Cache-Control"
    ] = "no-cache, no-store, must-revalidate"

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "Expires"
    ] = "0"


    return response
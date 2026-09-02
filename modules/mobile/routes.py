from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
    current_app,
    Response,
    flash
)

from functools import wraps

from config import DATA_FOLDER
from modules.mobile.survey_manager import SurveyManager

import pandas as pd
import os
import bcrypt


# ==========================================================
# DCGL FIELDMATE
# MOBILE BLUEPRINT
# ==========================================================

mobile_bp = Blueprint(
    "mobile",
    __name__,
    template_folder="../../templates/mobile"
)


# ==========================================================
# FIELDMATE USER FILE
# ==========================================================

USER_FILE = "users.xlsx"

MAX_ATTEMPTS = 3

failed_attempts = {}


# ==========================================================
# SURVEY MANAGER
# ==========================================================

survey_manager = SurveyManager(
    DATA_FOLDER
)


# ==========================================================
# LOAD USERS
# ==========================================================

def load_users():

    user_file = os.path.join(
        current_app.root_path,
        USER_FILE
    )

    if not os.path.exists(user_file):

        print(
            "FIELDMATE USER FILE NOT FOUND:",
            user_file
        )

        return {}

    try:

        df = pd.read_excel(
            user_file
        )

        users = {}

        for _, row in df.iterrows():

            username = str(
                row.get("Username", "")
            ).strip()

            password = row.get(
                "Password"
            )

            role = str(
                row.get("Role", "")
            ).strip()

            if not username:
                continue

            if pd.isna(password):
                continue

            users[username] = {

                "password":
                    str(password).strip(),

                "role":
                    role
            }

        return users

    except Exception as e:

        print(
            "FIELDMATE USER FILE ERROR:",
            e
        )

        return {}


# ==========================================================
# LOG ACTIVITY
# ==========================================================

def log_activity(
    username,
    action
):

    from datetime import datetime

    log_file = os.path.join(
        current_app.root_path,
        "user_log.txt"
    )

    try:

        with open(
            log_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"{datetime.now()} - "
                f"{username} "
                f"{action}\n"
            )

    except Exception as e:

        print(
            "FIELDMATE ACTIVITY LOG ERROR:",
            e
        )


# ==========================================================
# FIELDMATE LOGIN PROTECTION
# ==========================================================

def fieldmate_login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        # ==================================================
        # CHECK FIELDMATE SESSION ONLY
        # ==================================================

        if not session.get(
            "fieldmate_logged_in",
            False
        ):

            # ----------------------------------------------
            # NORMAL PAGE REQUEST
            # ----------------------------------------------

            if request.method == "GET":

                return redirect(
                    url_for(
                        "mobile.login",
                        next=request.full_path
                    )
                )

            # ----------------------------------------------
            # API REQUEST
            # ----------------------------------------------

            return jsonify({

                "success": False,

                "authenticated": False,

                "message":
                    "FieldMate login required."

            }), 401

        return view(
            *args,
            **kwargs
        )

    return wrapped_view


# ==========================================================
# FIELDMATE LOGIN
# ==========================================================

@mobile_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # ======================================================
    # ALREADY LOGGED INTO FIELDMATE
    # ======================================================

    if session.get(
        "fieldmate_logged_in",
        False
    ):

        return redirect(
            url_for(
                "mobile.mobile_home"
            )
        )


    # ======================================================
    # NEXT URL
    # ======================================================

    next_url = request.args.get(
        "next",
        ""
    )


    # ======================================================
    # LOGIN
    # ======================================================

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        next_url = request.form.get(
            "next",
            ""
        )

        users = load_users()


        # ==================================================
        # FAILED LOGIN LIMIT
        # ==================================================

        if (
            username in failed_attempts
            and
            failed_attempts[username]
            >= MAX_ATTEMPTS
        ):

            flash(
                "Too many failed attempts! "
                "Please reset your password.",
                "danger"
            )

            return redirect(
                url_for(
                    "mobile.login"
                )
            )


        # ==================================================
        # USER EXISTS
        # ==================================================

        if username in users:

            stored_hashed_password = \
                users[username]["password"]

            try:

                password_valid = bcrypt.checkpw(

                    password.encode(
                        "utf-8"
                    ),

                    stored_hashed_password.encode(
                        "utf-8"
                    )
                )

            except Exception as e:

                print(
                    "FIELDMATE PASSWORD CHECK ERROR:",
                    e
                )

                password_valid = False


            # ==================================================
            # SUCCESSFUL LOGIN
            # ==================================================

            if password_valid:

                # ------------------------------------------
                # IMPORTANT
                #
                # FieldMate has its OWN session.
                #
                # Do NOT write:
                #
                # session["username"]
                # session["role"]
                #
                # Those belong to the main system.
                # ------------------------------------------

                session["fieldmate_logged_in"] = True

                session["fieldmate_username"] = \
                    username

                session["fieldmate_role"] = \
                    users[username]["role"]


                # ------------------------------------------
                # RESET FAILED ATTEMPTS
                # ------------------------------------------

                failed_attempts[username] = 0


                # ------------------------------------------
                # LOG
                # ------------------------------------------

                log_activity(
                    username,
                    "logged in to FieldMate"
                )


                print("=" * 60)
                print("FIELDMATE LOGIN SUCCESS")
                print("=" * 60)
                print(
                    "FIELDMATE USER:",
                    username
                )
                print(
                    "FIELDMATE ROLE:",
                    users[username]["role"]
                )
                print("=" * 60)


                # ==================================================
                # RETURN TO REQUESTED FIELDMATE PAGE
                # ==================================================

                if (
                    next_url
                    and
                    next_url.startswith(
                        "/mobile/"
                    )
                ):

                    return redirect(
                        next_url
                    )


                return redirect(
                    url_for(
                        "mobile.mobile_home"
                    )
                )


            # ==================================================
            # INVALID PASSWORD
            # ==================================================

            failed_attempts[username] = \
                failed_attempts.get(
                    username,
                    0
                ) + 1


            log_activity(
                username,
                "failed FieldMate login"
            )


        # ==================================================
        # INVALID LOGIN
        # ==================================================

        flash(
            "Invalid username or password!",
            "danger"
        )

        return redirect(
            url_for(
                "mobile.login"
            )
        )


    # ======================================================
    # DISPLAY LOGIN PAGE
    # ======================================================

    return render_template(
        "mobile/login.html",
        next=next_url
    )


# ==========================================================
# FIELDMATE LOGOUT
# ==========================================================

@mobile_bp.route(
    "/logout"
)
def logout():

    # ======================================================
    # GET FIELDMATE USER
    # ======================================================

    username = session.get(
        "fieldmate_username",
        "Unknown"
    )


    # ======================================================
    # REMOVE ONLY FIELDMATE SESSION
    # ======================================================

    session.pop(
        "fieldmate_logged_in",
        None
    )

    session.pop(
        "fieldmate_username",
        None
    )

    session.pop(
        "fieldmate_role",
        None
    )


    # ======================================================
    # IMPORTANT
    #
    # DO NOT REMOVE:
    #
    # session["username"]
    # session["role"]
    #
    # because those may belong to the main system.
    # ======================================================


    log_activity(
        username,
        "logged out of FieldMate"
    )


    flash(
        "Logged out of FieldMate successfully.",
        "info"
    )


    return redirect(
        url_for(
            "mobile.login"
        )
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

        # ==================================================
        # RECEIVE DATA
        # ==================================================

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "message":
                    "No survey data received."

            }), 400


        # ==================================================
        # AUTHORITATIVE FIELDMATE USER
        # ==================================================

        username = session.get(
            "fieldmate_username",
            "Unknown"
        )


        # ==================================================
        # FORCE SERVER SURVEYOR
        #
        # Never trust the username sent by phone.
        # ==================================================

        data["surveyor"] = username


        # ==================================================
        # DEBUG
        # ==================================================

        print("=" * 60)
        print("MOBILE SURVEY SAVE")
        print("=" * 60)

        print(
            "FIELDMATE USER:",
            username
        )

        print(
            "FIELDMATE ROLE:",
            session.get(
                "fieldmate_role",
                ""
            )
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
        # REFRESH SURVEY MANAGER
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

        print(
            "SAVE SURVEY ERROR"
        )

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

@mobile_bp.route(
    "/survey_data"
)
@fieldmate_login_required
def survey_data():

    survey = SurveyManager(
        DATA_FOLDER
    )


    # ======================================================
    # AUTHORITATIVE FIELDMATE USER
    # ======================================================

    username = session.get(
        "fieldmate_username"
    )


    role = session.get(
        "fieldmate_role"
    )


    # ======================================================
    # SAFETY CHECK
    # ======================================================

    if not username:

        return jsonify({

            "success": False,

            "authenticated": False,

            "message":
                "FieldMate user identity is missing."

        }), 401


    print(
        "FIELDMATE SURVEY DATA:",
        username
    )


    return jsonify({

        "success": True,

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

        # --------------------------------------------------
        # AUTHORITATIVE USER
        # --------------------------------------------------

        "surveyor":
            username,

        "role":
            role or ""

    })



# ==========================================================
# NEXT AVAILABLE SUB-FIELD
# ==========================================================

@mobile_bp.route(
    "/next_subfield/<parent>"
)
@fieldmate_login_required
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
@fieldmate_login_required
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

        print(
            "PARENT AREA ERROR"
        )

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
    # Physical file:
    #
    # static/mobile/service-worker.js
    #
    # Browser URL:
    #
    # /mobile/service-worker.js
    #
    # ------------------------------------------------------

    sw_path = os.path.join(

        current_app.static_folder,

        "mobile",

        "service-worker.js"

    )


    # ======================================================
    # CHECK FILE
    # ======================================================

    if not os.path.exists(sw_path):

        print(
            "SERVICE WORKER NOT FOUND:",
            sw_path
        )

        return (
            "Service Worker not found.",
            404
        )


    # ======================================================
    # READ FILE
    # ======================================================

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


    # ======================================================
    # RETURN JAVASCRIPT
    # ======================================================

    response = Response(

        content,

        mimetype="application/javascript"

    )


    # ======================================================
    # ALLOW SERVICE WORKER TO CONTROL /mobile/
    # ======================================================

    response.headers[
        "Service-Worker-Allowed"
    ] = "/mobile/"


    # ======================================================
    # DEVELOPMENT CACHE CONTROL
    # ======================================================

    response.headers[
        "Cache-Control"
    ] = (
        "no-cache, "
        "no-store, "
        "must-revalidate"
    )

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "Expires"
    ] = "0"


    return response


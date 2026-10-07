from flask import Blueprint, render_template, session, redirect, url_for, request, flash
import os
import pandas as pd
from modules.helpers import get_active_season  # assuming you're using helper functions
from modules.utils import role_required
import json
from modules.gdrive_sync import upload_excel_to_drive
from flask import request, jsonify
from modules.fertilizer_programme import (
    generate_fertilizer_programme,
    calculate_urea_requirement
)
from datetime import datetime, timedelta

activity_bp = Blueprint('activities', __name__)

@activity_bp.route('/agriculture/activities')
def farm_activities():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('agriculture/farm_activities.html', username=session['username'])

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
import pandas as pd
from modules.season import get_active_season


PLANTING_FILE = "data/planting_records.xlsx"

@activity_bp.route('/agriculture/planting', methods=["GET", "POST"])
def planting():
    if 'username' not in session:
        return redirect(url_for('login'))

    season = get_active_season()

    if request.method == "POST":
        # Get labor values safely
        capitao = int(request.form.get("Capitao") or 0)
        planters = int(request.form.get("Planters") or 0)
        choppers = int(request.form.get("Choppers") or 0)
        gleaners = int(request.form.get("Gleaners") or 0)
        water_drawers = int(request.form.get("Water Drawers") or 0)
        tools_keeper = int(request.form.get("Tools Keeper") or 0)
        transporters = int(request.form.get("Transporters") or 0)

        # Auto-calculate mandays (capitao + planters + others)
        mandays = capitao + planters + choppers + gleaners + water_drawers + tools_keeper + transporters

        form_data = {
            "Date": request.form.get("Date"),
            "Field": request.form.get("Field"),
            "Crop Type": request.form.get("Crop Type"),
            "Seed Variety": request.form.get("Seed Variety"),
            "Planted Area (ha)": request.form.get("Planted Area (ha)"),
            "Bundles Used": request.form.get("Bundles Used"),
            "Capitao": capitao,
            "Planters": planters,
            "Choppers": choppers,
            "Gleaners": gleaners,
            "Water Drawers": water_drawers,
            "Tools Keeper": tools_keeper,
            "Transporters": transporters,
            "Mandays": mandays,
            "Notes": request.form.get("Notes"),
            "Season": season
        }

        try:
            # Load existing data or create empty DataFrame
            if os.path.exists(PLANTING_FILE):
                df = pd.read_excel(PLANTING_FILE)
            else:
                df = pd.DataFrame()

            # Ensure all keys from form_data exist as columns
            for column in form_data.keys():
                if column not in df.columns:
                    df[column] = None  # Fill missing columns with NaN

            # Append new data
            df = pd.concat([df, pd.DataFrame([form_data])], ignore_index=True)

            # Reorder columns to match form_data
            df = df[list(form_data.keys())]

            # Save to Excel
            df.to_excel(PLANTING_FILE, index=False)
            flash("✅ Planting activity saved successfully!", "success")

        except Exception as e:
            flash(f"❌ Error saving data: {e}", "danger")

    return render_template('agriculture/planting.html', season=season)


@activity_bp.route('/planting_report', methods=['GET', 'POST'])
def planting_report():

    if not os.path.exists(PLANTING_FILE):

        flash(
            "No planting records found.",
            "warning"
        )

        return redirect(
            url_for('activities.planting')
        )

    df = pd.read_excel(
        PLANTING_FILE
    )

    if "Season" not in df.columns:

        flash(
            "No 'Season' column found in data.",
            "danger"
        )

        return redirect(
            url_for('activities.planting')
        )

    seasons = sorted(

        df["Season"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()

    )

    if not seasons:

        flash(
            "No seasons found.",
            "warning"
        )

        return redirect(
            url_for('activities.planting')
        )

    selected_season = (

            request.form.get("season")

            or seasons[-1]

    )

    df = df[

        df["Season"].astype(str)

        == selected_season

    ].copy()

    if df.empty:

        flash(

            f"No planting data found for season {selected_season}.",

            "info"

        )

        return redirect(

            url_for('activities.planting')

        )

    # ------------------------------------------------
    # Dates
    # ------------------------------------------------

    df["Date"] = pd.to_datetime(

        df["Date"],

        errors="coerce"

    )

    # ------------------------------------------------
    # Numeric columns
    # ------------------------------------------------

    labor_cols = [

        "Capitao",

        "Planters",

        "Choppers",

        "Gleaners",

        "Water Drawers",

        "Tools Keeper",

        "Transporters"

    ]

    numeric_cols = [

        "Planted Area (ha)",

        "Bundles Used"

    ]

    for col in labor_cols + numeric_cols:

        if col in df.columns:

            df[col] = pd.to_numeric(

                df[col],

                errors="coerce"

            ).fillna(0)

    # ------------------------------------------------
    # Mandays
    # ------------------------------------------------

    df["Mandays"] = 0

    for col in labor_cols:

        if col in df.columns:

            df["Mandays"] += df[col]

    # ------------------------------------------------
    # KPIs
    # ------------------------------------------------

    total_dates = (

        df["Date"]

        .nunique()

    )

    total_fields = (

        df["Field"]

        .nunique()

        if "Field" in df.columns

        else 0

    )

    total_area = round(

        df["Planted Area (ha)"]

        .sum(),

        2

    )

    total_bundles = round(

        df["Bundles Used"]

        .sum(),

        2

    )

    labor_totals = {

        col:

            round(

                df[col].sum(),

                0

            )

        for col in labor_cols

        if col in df.columns

    }

    total_labor = round(

        df["Mandays"]

        .sum(),

        0

    )

    avg_area_per_day = round(

        total_area /

        total_dates,

        2

    ) if total_dates else 0

    seed_rate = round(

        total_bundles /

        total_area,

        2

    ) if total_area else 0

    labor_per_ha = round(

        total_labor /

        total_area,

        2

    ) if total_area else 0

    # ------------------------------------------------
    # Peak planting day
    # ------------------------------------------------

    peak_day = ""

    peak_area = 0

    daily = (

        df.groupby(

            "Date"

        )[

            "Planted Area (ha)"

        ]

        .sum()

    )

    if not daily.empty:

        peak_day = (

            daily.idxmax()

        )

        peak_area = round(

            daily.max(),

            2

        )

        if pd.notna(

                peak_day

        ):

            peak_day = (

                peak_day

                .strftime(

                    "%Y-%m-%d"

                )

            )

    # ------------------------------------------------
    # FIELD SUMMARY
    # ------------------------------------------------

    field_summary = (

        df.groupby(

            "Field"

        )

        .agg({

            "Date": [

                "min",

                "max",

                "nunique"

            ],

            "Planted Area (ha)": "sum",

            "Bundles Used": "sum",

            "Mandays": "sum"

        })

        .reset_index()

    )

    field_summary.columns = [

        "Field",

        "First Planting",

        "Last Planting",

        "Days Worked",

        "Area",

        "Bundles",

        "Mandays"

    ]

    field_summary["Bundles per ha"] = (

        field_summary["Bundles"]

        /

        field_summary["Area"]

    ).round(2)

    field_summary["Mandays per ha"] = (

        field_summary["Mandays"]

        /

        field_summary["Area"]

    ).round(2)

    field_summary["First Planting"] = (

        field_summary["First Planting"]

        .dt.strftime(

            "%Y-%m-%d"

        )

    )

    field_summary["Last Planting"] = (

        field_summary["Last Planting"]

        .dt.strftime(

            "%Y-%m-%d"

        )

    )

    field_summary = (

        field_summary

        .sort_values(

            by="Area",

            ascending=False

        )

    )

    field_records = (

        field_summary

        .to_dict(

            orient="records"

        )

    )

    return render_template(

        "agriculture/planting_report.html",

        seasons=seasons,

        selected_season=selected_season,

        total_dates=total_dates,

        total_area=total_area,

        total_bundles=total_bundles,

        total_labor=total_labor,

        labor_totals=labor_totals,

        total_fields=total_fields,

        avg_area_per_day=avg_area_per_day,

        seed_rate=seed_rate,

        labor_per_ha=labor_per_ha,

        peak_day=peak_day,

        peak_area=peak_area,

        field_records=field_records

    )


WEEDING_FILE = "data/weeding_records.xlsx"

@activity_bp.route('/agriculture/weeding', methods=["GET", "POST"])
def weeding():
    if 'username' not in session:
        return redirect(url_for('login'))
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == "POST":
        form_data = {
            "Date": request.form.get("Date"),
            "Field": request.form.get("Field"),
            "Method Used": request.form.get("Method Used"),
            "Weeded Area (ha)": request.form.get("Weeded Area (ha)"),
            "Mandays": request.form.get("Mandays"),
            "Season": season
        }

        try:
            df = pd.read_excel(WEEDING_FILE) if os.path.exists(WEEDING_FILE) else pd.DataFrame()
            df = pd.concat([df, pd.DataFrame([form_data])], ignore_index=True)
            df.to_excel(WEEDING_FILE, index=False)
            flash("Weeding activity saved successfully!", "success")
        except Exception as e:
            flash(f"Error saving data: {e}", "danger")

    return render_template('agriculture/weeding.html', season=season)

@activity_bp.route('/weeding_report', methods=['GET', 'POST'])
def weeding_report():
    if not os.path.exists(WEEDING_FILE):
        flash("No weeding records found.", "warning")
        return redirect(url_for('activities.weeding'))

    df = pd.read_excel(WEEDING_FILE)

    if "Season" not in df.columns:
        flash("No 'Season' column found in weeding data.", "danger")
        return redirect(url_for('activities.weeding'))

    seasons = sorted(df["Season"].dropna().unique().tolist())
    selected_season = request.form.get("season") or seasons[-1]

    df = df[df["Season"] == selected_season]

    if df.empty:
        flash(f"No weeding data found for season {selected_season}.", "info")
        return redirect(url_for('activities.weeding'))

    # Ensure numeric
    for col in ["Weeded Area (ha)", "Mandays"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    total_dates = df['Date'].nunique()
    total_area = df['Weeded Area (ha)'].sum()
    total_mandays = df['Mandays'].sum()
    avg_area_per_day = total_area / total_dates if total_dates else 0

    return render_template(
        "agriculture/weeding_report.html",
        seasons=seasons,
        selected_season=selected_season,
        total_dates=total_dates,
        total_area=total_area,
        total_mandays=total_mandays,
        avg_area_per_day=avg_area_per_day,
        table=df.to_dict(orient='records')
    )

from flask import request, render_template, redirect, url_for, flash, session
import pandas as pd
import os
from modules.gdrive_sync import upload_excel_to_drive  # Only if you're using GDrive sync

IRRIGATION_FILE = 'data/irrigation_data.xlsx'

@activity_bp.route("/irrigation", methods=["GET", "POST"])
def irrigation():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        try:
            date = request.form["date"]
            field = request.form["field"]
            irrigation = float(request.form["irrigation"])

            # Get current active season
            from modules.season import get_active_season
            season = get_active_season()

            new_entry = {
                "Date": pd.to_datetime(date).date(),
                "Field": field,
                "Irrigation Applied": irrigation,
                "Season": season
            }

            if os.path.exists(IRRIGATION_FILE):
                df = pd.read_excel(IRRIGATION_FILE)
                if 'Season' not in df.columns:
                    df['Season'] = ''
            else:
                df = pd.DataFrame(columns=["Date", "Field", "Irrigation Applied", "Season"])

            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_excel(IRRIGATION_FILE, index=False)

            # Optional: Upload to Google Drive
            try:
                upload_excel_to_drive(IRRIGATION_FILE)
            except Exception as sync_err:
                print("Google Drive sync failed:", sync_err)

            # 🔁 Trigger stress level recalculation
            try:
                from modules.recalc import recalculate_stress
                recalculate_stress()
                flash("✅ Irrigation record saved and stress levels updated!", "success")
            except Exception as e:
                flash(f"✅ Irrigation saved, but stress update failed: {e}", "warning")

        except Exception as e:
            flash(f"❌ Failed to save record: {e}", "danger")

        return redirect(url_for("activities.irrigation"))

    return render_template("agriculture/irrigation.html")


from flask import request, render_template, redirect, url_for, flash
import pandas as pd
import os

# Constants
IRRIGATION_FILE = "data/irrigation_records.xlsx"
WEATHER_FILE = "data/weather_data.xlsx"
WHC = 100  # Water Holding Capacity (mm)
SM_i = 5   # Initial Soil Moisture (mm)

@activity_bp.route("/irrigation")
def irrigation_dashboard():
    irrigation = pd.read_excel(IRRIGATION_FILE)
    # Strip column names just in case
    irrigation.columns = irrigation.columns.str.strip()

    # Ensure Field is string
    fields = irrigation["Field"].dropna().astype(str).unique().tolist()

    return render_template(
        "agriculture/irrigation.html",
        fields=fields
    )



from flask import jsonify

@activity_bp.route("/api/moisture-data")
def api_moisture_data():
    field = request.args.get("field")
    start_date = pd.to_datetime(request.args.get("start"))
    end_date = pd.to_datetime(request.args.get("end"))

    # Load data
    weather = pd.read_excel(WEATHER_FILE)
    irrigation = pd.read_excel(IRRIGATION_FILE)

    weather["Date"] = pd.to_datetime(weather["Date"])
    irrigation["Date"] = pd.to_datetime(irrigation["Date"])

    irrigation = irrigation[irrigation["Field"] == field]

    # Full date range
    full_dates = pd.date_range(
        start=weather["Date"].min(),
        end=weather["Date"].max()
    )

    df = pd.DataFrame({"Date": full_dates})
    df = df.merge(weather, on="Date", how="left").fillna(0)
    df = df.merge(
        irrigation[["Date", "Irrigation Applied"]],
        on="Date",
        how="left"
    ).fillna(0)

    # === SOIL MOISTURE MODEL (UNCHANGED) ===
    moisture = [SM_i]

    for i in range(1, len(df)):
        net_input = (
            df.loc[i, "Rainfall"]
            + df.loc[i, "Irrigation Applied"]
            - df.loc[i, "Evapotranspiration"]
        )

        value = max(0, min(WHC, moisture[-1] + net_input))
        moisture.append(value)

    df["Soil_Moisture"] = moisture
    df["Deficit"] = WHC - df["Soil_Moisture"]

    # Filter date range
    df = df[
        (df["Date"] >= start_date) &
        (df["Date"] <= end_date)
    ]

    # === JSON FOR CHART.JS ===
    return jsonify({
        "dates": df["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "deficit": df["Deficit"].tolist(),
        "rainfall": df["Rainfall"].tolist(),
        "irrigation": df["Irrigation Applied"].tolist(),
        "threshold": [50] * len(df)  # stress line
    })




@activity_bp.route('/agriculture/irrigation-report')
def irrigation_report():
    import pandas as pd
    from flask import request, render_template, flash

    IRRIGATION_FILE = "data/irrigation_records.xlsx"
    records = []
    fields = []
    seasons = []
    selected_field = request.args.get('field', '')
    selected_season = request.args.get('season', '')

    try:
        df = pd.read_excel(IRRIGATION_FILE)

        # Extract filter options
        fields = sorted(df['Field'].dropna().unique())
        seasons = sorted(df['Season'].dropna().unique()) if 'Season' in df.columns else []

        # Apply filters
        if selected_field:
            df = df[df['Field'] == selected_field]
        if selected_season:
            df = df[df['Season'] == selected_season]

        # Convert records to dictionaries for Jinja2
        records = df.to_dict(orient='records')

    except FileNotFoundError:
        flash("Irrigation data file not found.", "danger")
    except Exception as e:
        flash(f"Error loading irrigation report: {e}", "danger")

    return render_template(
        'agriculture/irrigation_report.html',
        records=records,
        fields=fields,
        seasons=seasons,
        field=selected_field,
        season=selected_season
    )


# modules/pest_disease.py

pest_bp = Blueprint('pest', __name__)
PEST_DISEASE_FILE = "data/pest_disease_control.xlsx"

@activity_bp.route("/agriculture/pest-disease", methods=["GET", "POST"])
def pest_disease():
    if 'username' not in session:
        return redirect(url_for('login'))
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "disease":
            fields = ["Date", "Field", "Variety", "SMUT%", "YSA%", "Black Beetles (ha)", "Lady Beetle", "Mandays", "Season"]
            data = {f: request.form.get(f) for f in fields}
        elif form_type == "pest":
            fields = ["Date", "Field", "Hectares", "Pesticide Used", "Liters", "Mandays", "Season"]
            data = {f: request.form.get(f) for f in fields}
        else:
            flash("Invalid form submission", "danger")
            return redirect(url_for("pest.pest_disease"))

        data["Season"] = season
        df = pd.read_excel(PEST_DISEASE_FILE) if os.path.exists(PEST_DISEASE_FILE) else pd.DataFrame(columns=data.keys())
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_excel(PEST_DISEASE_FILE, index=False)

        flash("Record saved successfully!", "success")
        return redirect(url_for("activities.pest_disease"))

    return render_template("agriculture/pest_disease.html", season=season)


@activity_bp.route('/agriculture/pest-disease-report', methods=['GET', 'POST'])
def pest_disease_report():
    import pandas as pd
    from flask import request, render_template, flash

    PEST_DISEASE_FILE = "data/pest_disease_control.xlsx"
    from modules.season import get_active_season

    season = get_active_season()
    selected_field = None
    all_fields = []
    records = []
    chart_data = None

    try:
        df = pd.read_excel(PEST_DISEASE_FILE)

        # Filter by season
        if 'Season' in df.columns:
            df = df[df['Season'] == season]

        df = df.dropna(subset=['Field'])
        all_fields = sorted(df['Field'].unique())

        # Convert dates early
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

        # Field filtering (if POST)
        if request.method == 'POST':
            selected_field = request.form.get('field')
            if selected_field:
                df = df[df['Field'] == selected_field]

        # Convert table to dict
        if not df.empty:
            df = df.sort_values(by='Date')
            records = df.to_dict(orient='records')

            # Compute chart dataset
            if {'SMUT%', 'YSA%', 'Date'}.issubset(df.columns):

                # 📌 If field selected → use raw date points
                if selected_field:
                    df['DateLabel'] = df['Date'].dt.strftime('%Y-%m-%d')

                    chart_data = {
                        "labels": df['DateLabel'].tolist(),
                        "smut": df['SMUT%'].round(2).fillna(0).tolist(),
                        "ysa": df['YSA%'].round(2).fillna(0).tolist()
                    }

                # 📌 No field selected → monthly averages
                else:
                    df['MonthPeriod'] = df['Date'].dt.to_period('M')
                    grouped = (
                        df.groupby('MonthPeriod')
                        .agg({'SMUT%': 'mean', 'YSA%': 'mean'})
                        .reset_index()
                    )

                    grouped['Month'] = grouped['MonthPeriod'].dt.to_timestamp()
                    grouped = grouped.sort_values(by='Month')
                    grouped['MonthLabel'] = grouped['Month'].dt.strftime('%b-%Y')

                    chart_data = {
                        "labels": grouped['MonthLabel'].tolist(),
                        "smut": grouped['SMUT%'].round(2).fillna(0).tolist(),
                        "ysa": grouped['YSA%'].round(2).fillna(0).tolist()
                    }

    except FileNotFoundError:
        flash("Pest & Disease data file not found.", "danger")
    except Exception as e:
        flash(f"Error loading pest & disease data: {e}", "danger")

    return render_template(
        'agriculture/pest_disease_report.html',
        records=records,
        all_fields=all_fields,
        chart_data=chart_data,
        season=season,
        current_field=selected_field
    )


HERBICIDE_FILE = "data/herbicide_records.xlsx"


# ==========================================================
# HERBICIDE MODULE MENU
# ==========================================================

@activity_bp.route(
    "/agriculture/herbicide-menu",
    methods=["GET"]
)
def herbicide_menu():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    # ------------------------------------------------------
    # ACTIVE SEASON
    # ------------------------------------------------------

    from modules.season import get_active_season

    season = get_active_season()


    # ------------------------------------------------------
    # RENDER MENU
    # ------------------------------------------------------

    return render_template(
        "agriculture/herbicide_menu.html",
        season=season
    )

# ==========================================================
# SYNC ACTUAL HERBICIDE APPLICATION TO PROGRAMME
# ==========================================================

def sync_herbicide_application_to_programme(
    application_data
):
    """
    Synchronise an actual herbicide application with the
    generated herbicide programme.

    Matching is based on:

        Season
        Field
        Chemical / Chemical Cocktail

    If more than one matching programme entry exists,
    the unapplied entry whose Planned Date is closest to
    the actual application Date is selected.

    Once matched:

        Actual Date
        Actual Quantity
        Status

    are updated in herbicide_schedule.xlsx.
    """

    try:

        # ==================================================
        # LOAD PROGRAMME
        # ==================================================

        programme_df = load_herbicide_schedule()

        if programme_df.empty:

            print(
                "[HERBICIDE SYNC] "
                "Herbicide programme is empty."
            )

            return False

        # ==================================================
        # APPLICATION DATE
        # ==================================================

        application_date = pd.to_datetime(
            application_data.get(
                "Date",
                ""
            ),
            errors="coerce"
        )

        if pd.isna(application_date):

            print(
                "[HERBICIDE SYNC] "
                "Invalid application date."
            )

            return False

        application_date = (
            application_date.normalize()
        )

        # ==================================================
        # SEASON
        # ==================================================

        application_season = str(
            application_data.get(
                "Season",
                ""
            )
        ).strip()

        season_normalised = (
            application_season
            .replace(
                " ",
                ""
            )
            .lower()
        )

        # ==================================================
        # FIELD
        # ==================================================

        application_field = str(
            application_data.get(
                "Field",
                ""
            )
        ).strip()

        field_normalised = (
            application_field
            .lower()
        )

        if not application_field:

            print(
                "[HERBICIDE SYNC] "
                "Application field is empty."
            )

            return False

        # ==================================================
        # CHEMICAL COLUMNS
        # ==================================================

        chemical_columns = [

            "MSMA",
            "MCPA",
            "Ametryn",
            "Altrazine",
            "Servian WP",
            "Round-Up",
            "Dual Magnum",
            "Sprint",
            "Garlon",
            "Acetochlor",
            "Metolachlor",
            "BB5"

        ]

        # ==================================================
        # FIND CHEMICALS ACTUALLY USED
        # ==================================================

        applied_chemicals = []

        for chemical in chemical_columns:

            value = application_data.get(
                chemical,
                ""
            )

            if value is None:
                continue

            value_text = str(
                value
            ).strip()

            if not value_text:
                continue

            # ------------------------------------------------
            # Ignore zero quantities
            # ------------------------------------------------

            try:

                numeric_value = float(
                    value_text
                )

                if numeric_value == 0:
                    continue

            except Exception:
                pass

            applied_chemicals.append(
                chemical
            )

        # ==================================================
        # NORMALISE PROGRAMME SEASON
        # ==================================================

        programme_df["_SeasonNormalised"] = (
            programme_df["Season"]
            .astype(str)
            .str.strip()
            .str.replace(
                " ",
                "",
                regex=False
            )
            .str.lower()
        )

        # ==================================================
        # NORMALISE PROGRAMME FIELD
        # ==================================================

        programme_df["_FieldNormalised"] = (
            programme_df["Field"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # ==================================================
        # NORMALISE PROGRAMME CHEMICALS
        # ==================================================

        def normalise_chemical_list(
            chemical_text
        ):
            """
            Convert:

                Ametryn + MCPA

            into:

                {"ametryn", "mcpa"}
            """

            if chemical_text is None:
                return set()

            text = str(
                chemical_text
            ).strip().lower()

            if not text:
                return set()

            return {
                item.strip()
                for item in text.split("+")
                if item.strip()
            }

        applied_chemical_set = {
            chemical.strip().lower()
            for chemical in applied_chemicals
        }

        # ==================================================
        # FIRST MATCH:
        #
        # SEASON + FIELD
        # ==================================================

        candidates = programme_df[
            (
                programme_df[
                    "_SeasonNormalised"
                ]
                ==
                season_normalised
            )
            &
            (
                programme_df[
                    "_FieldNormalised"
                ]
                ==
                field_normalised
            )
        ].copy()

        if candidates.empty:

            print(
                "[HERBICIDE SYNC] "
                f"No programme entries found for "
                f"{application_field} / "
                f"{application_season}."
            )

            programme_df.drop(
                columns=[
                    "_SeasonNormalised",
                    "_FieldNormalised"
                ],
                inplace=True,
                errors="ignore"
            )

            return False

        # ==================================================
        # REMOVE ALREADY APPLIED ENTRIES
        # ==================================================

        candidates = candidates[
            candidates["Actual Date"].apply(
                lambda value:
                pd.isna(
                    pd.to_datetime(
                        value,
                        errors="coerce"
                    )
                )
            )
        ].copy()

        if candidates.empty:

            print(
                "[HERBICIDE SYNC] "
                f"No unapplied programme entries "
                f"remain for {application_field}."
            )

            programme_df.drop(
                columns=[
                    "_SeasonNormalised",
                    "_FieldNormalised"
                ],
                inplace=True,
                errors="ignore"
            )

            return False

        # ==================================================
        # CHEMICAL MATCH
        # ==================================================

        if applied_chemical_set:

            def chemical_set_matches(
                programme_chemical
            ):

                programme_chemical_set = (
                    normalise_chemical_list(
                        programme_chemical
                    )
                )

                return (
                    programme_chemical_set
                    ==
                    applied_chemical_set
                )

            chemical_matches = candidates[
                candidates["Chemical"].apply(
                    chemical_set_matches
                )
            ].copy()

            # ------------------------------------------------
            # If exact cocktail matching found entries,
            # use only those.
            # ------------------------------------------------

            if not chemical_matches.empty:

                candidates = (
                    chemical_matches
                )

            else:

                print(
                    "[HERBICIDE SYNC] "
                    "No exact chemical combination match "
                    f"for field {application_field}. "
                    f"Application chemicals: "
                    f"{', '.join(applied_chemicals)}"
                )

                programme_df.drop(
                    columns=[
                        "_SeasonNormalised",
                        "_FieldNormalised"
                    ],
                    inplace=True,
                    errors="ignore"
                )

                return False

        else:

            print(
                "[HERBICIDE SYNC] "
                "No chemical quantity was entered "
                "for the application."
            )

            programme_df.drop(
                columns=[
                    "_SeasonNormalised",
                    "_FieldNormalised"
                ],
                inplace=True,
                errors="ignore"
            )

            return False

        # ==================================================
        # PLANNED DATE
        # ==================================================

        candidates["_PlannedDate"] = (
            pd.to_datetime(
                candidates[
                    "Planned Date"
                ],
                errors="coerce"
            )
        )

        # ==================================================
        # DATE DIFFERENCE
        # ==================================================

        candidates["_DateDifference"] = (
            (
                candidates[
                    "_PlannedDate"
                ]
                -
                application_date
            )
            .abs()
        )

        # ==================================================
        # CLOSEST PROGRAMME ENTRY
        # ==================================================

        candidates = candidates.sort_values(
            [
                "_DateDifference",
                "_PlannedDate"
            ],
            na_position="last"
        )

        matched_index = (
            candidates.index[0]
        )

        matched_row = (
            programme_df.loc[
                matched_index
            ]
        )

        matched_programme_id = str(
            matched_row.get(
                "Programme ID",
                ""
            )
        ).strip()

        matched_chemical = str(
            matched_row.get(
                "Chemical",
                ""
            )
        ).strip()

        matched_planned_date = pd.to_datetime(
            matched_row.get(
                "Planned Date"
            ),
            errors="coerce"
        )

        # ==================================================
        # BUILD ACTUAL QUANTITY
        # ==================================================
        #
        # For a cocktail:
        #
        #     Ametryn + MCPA
        #
        # and actual quantities:
        #
        #     Ametryn = 6
        #     MCPA    = 7.5
        #
        # store:
        #
        #     6 + 7.5
        #
        # in the same order as the programme chemical.
        #

        programme_chemicals = [
            item.strip()
            for item in matched_chemical.split("+")
            if item.strip()
        ]

        actual_quantity_parts = []

        for programme_chemical in (
            programme_chemicals
        ):

            matched_column = None

            for application_chemical in (
                chemical_columns
            ):

                if (
                    application_chemical
                    .strip()
                    .lower()
                    ==
                    programme_chemical
                    .strip()
                    .lower()
                ):

                    matched_column = (
                        application_chemical
                    )

                    break

            if matched_column is None:
                continue

            value = application_data.get(
                matched_column,
                ""
            )

            value_text = str(
                value
            ).strip()

            if value_text:

                actual_quantity_parts.append(
                    value_text
                )

        actual_quantity = (
            " + ".join(
                actual_quantity_parts
            )
            if actual_quantity_parts
            else ""
        )

        # ==================================================
        # UPDATE PROGRAMME ROW
        # ==================================================

        programme_df.at[
            matched_index,
            "Actual Date"
        ] = application_date

        programme_df.at[
            matched_index,
            "Actual Quantity"
        ] = actual_quantity

        programme_df.at[
            matched_index,
            "Status"
        ] = "APPLIED"

        # ==================================================
        # CLEAN TEMPORARY COLUMNS
        # ==================================================

        programme_df.drop(
            columns=[
                "_SeasonNormalised",
                "_FieldNormalised",
                "_PlannedDate",
                "_DateDifference"
            ],
            inplace=True,
            errors="ignore"
        )

        # ==================================================
        # SAVE PROGRAMME
        # ==================================================

        save_herbicide_schedule(
            programme_df
        )

        # ==================================================
        # DIAGNOSTIC
        # ==================================================

        print(
            "=================================================="
        )

        print(
            "[HERBICIDE SYNC] "
            "APPLICATION MATCHED"
        )

        print(
            f"Programme ID: "
            f"{matched_programme_id}"
        )

        print(
            f"Field: "
            f"{application_field}"
        )

        print(
            f"Chemical: "
            f"{matched_chemical}"
        )

        print(
            f"Planned Date: "
            f"{matched_planned_date}"
        )

        print(
            f"Actual Date: "
            f"{application_date}"
        )

        print(
            f"Actual Quantity: "
            f"{actual_quantity}"
        )

        print(
            "Status: APPLIED"
        )

        print(
            "=================================================="
        )

        return True

    except Exception as e:

        print(
            "[HERBICIDE SYNC ERROR] "
            f"{e}"
        )

        return False

# ==========================================================
# HERBICIDE ACTUAL APPLICATION
# ==========================================================

@activity_bp.route(
    "/agriculture/herbicide",
    methods=["GET", "POST"]
)
def herbicide():

    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    # ======================================================
    # HERBICIDE APPLICATION COLUMNS
    # ======================================================

    fields = [

        "Date",

        "Field",

        "Crop Type",

        "Applied Area (ha)",

        "MSMA",

        "MCPA",

        "Ametryn",

        "Altrazine",

        "Servian WP",

        "Round-Up",

        "Dual Magnum",

        "Sprint",

        "Garlon",

        "Acetochlor",

        "Metolachlor",

        "BB5",

        "Mandays",

        "Season"

    ]

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        try:

            # ==================================================
            # ACTIVE SEASON
            # ==================================================

            season = get_active_season()

            # ==================================================
            # READ FORM
            # ==================================================

            data = {
                field:
                    request.form.get(
                        field,
                        ""
                    )
                for field in fields
            }

            # ==================================================
            # FORCE ACTIVE SEASON
            # ==================================================

            data["Season"] = season

            # ==================================================
            # BASIC VALIDATION
            # ==================================================

            if not str(
                data.get(
                    "Date",
                    ""
                )
            ).strip():

                flash(
                    "Please enter the herbicide application date.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "activities.herbicide"
                    )
                )

            if not str(
                data.get(
                    "Field",
                    ""
                )
            ).strip():

                flash(
                    "Please select a field.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "activities.herbicide"
                    )
                )

            # ==================================================
            # LOAD EXISTING HERBICIDE RECORDS
            # ==================================================

            if os.path.exists(
                HERBICIDE_FILE
            ):

                df = pd.read_excel(
                    HERBICIDE_FILE,
                    engine="openpyxl"
                )

            else:

                df = pd.DataFrame(
                    columns=fields
                )

            # ==================================================
            # ENSURE COLUMNS EXIST
            # ==================================================

            for column in fields:

                if column not in df.columns:

                    df[column] = ""

            # ==================================================
            # STANDARD COLUMN ORDER
            # ==================================================

            df = df[
                fields
            ].copy()

            # ==================================================
            # APPEND APPLICATION
            # ==================================================

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [data]
                    )
                ],
                ignore_index=True
            )

            # ==================================================
            # SAVE ACTUAL APPLICATION
            # ==================================================

            os.makedirs(
                os.path.dirname(
                    HERBICIDE_FILE
                ),
                exist_ok=True
            )

            df.to_excel(
                HERBICIDE_FILE,
                index=False
            )

            # ==================================================
            # SYNCHRONISE WITH PROGRAMME
            # ==================================================

            synced = (
                sync_herbicide_application_to_programme(
                    data
                )
            )

            # ==================================================
            # SUCCESS MESSAGE
            # ==================================================

            if synced:

                flash(
                    "Herbicide application saved successfully "
                    "and the matching programme entry was "
                    "updated to APPLIED.",
                    "success"
                )

            else:

                flash(
                    "Herbicide application was saved successfully, "
                    "but no matching herbicide programme entry "
                    "could be found.",
                    "warning"
                )

            # ==================================================
            # RETURN TO APPLICATION PAGE
            # ==================================================

            return redirect(
                url_for(
                    "activities.herbicide"
                )
            )

        except Exception as e:

            print(
                "[HERBICIDE APPLICATION ERROR] "
                f"{e}"
            )

            flash(
                f"Error saving herbicide application: {e}",
                "danger"
            )

    # ======================================================
    # GET
    # ======================================================

    return render_template(
        "agriculture/herbicide.html",
        season=get_active_season()
    )


@activity_bp.route('/agriculture/herbicide-report')
def herbicide_report():
    try:
        HERBICIDE_FILE = "data/herbicide_records.xlsx"
        from modules.season import get_active_season
        season = get_active_season()

        if not os.path.exists(HERBICIDE_FILE):
            flash("No herbicide records found.", "warning")
            return render_template("agriculture/herbicide_report.html", records=[], fields=[], chemicals=[], season=season)

        df = pd.read_excel(HERBICIDE_FILE)
        df = df[df["Season"] == season] if "Season" in df.columns else df

        # Fetch filters from query params
        selected_field = request.args.get("field")
        selected_chemical = request.args.get("chemical")

        # Apply filters
        if selected_field:
            df = df[df["Field"] == selected_field]

        if selected_chemical and selected_chemical in df.columns:
            df = df[df[selected_chemical] > 0]

        # Get unique field and chemical options
        field_options = sorted(df["Field"].dropna().unique().tolist())
        chemical_columns = ["MSMA", "MCPA", "Ametryn", "Altrazine", "Servian WP", "Round-Up",
                            "Dual Magnum", "Sprint", "Garlon", "Acetochlor", "Metolachlor", "BB5"]
        existing_chemicals = [chem for chem in chemical_columns if chem in df.columns]

        return render_template("agriculture/herbicide_report.html",
                               records=df.to_dict(orient="records"),
                               fields=field_options,
                               chemicals=existing_chemicals,
                               selected_field=selected_field,
                               selected_chemical=selected_chemical,
                               season=season)

    except Exception as e:
        flash(f"Error loading report: {e}", "danger")
        return render_template("agriculture/herbicide_report.html", records=[], fields=[], chemicals=[], season="Unknown")

# ==========================================================
# HERBICIDE MODULE
# ==========================================================
#
# DCGL HERBICIDE MANAGEMENT
#
# IMPORTANT DESIGN PRINCIPLES
#
# 1. herbicide_chemical_catalogue.xlsx is the SINGLE SOURCE
#    OF TRUTH for:
#
#       - Chemical
#       - Rate
#       - Rate Unit
#       - Season
#       - Active
#       - Notes
#
# 2. Herbicide rules DO NOT manually maintain chemical rates.
#
# 3. Herbicide rules reference chemicals from the active
#    season catalogue.
#
# 4. Cocktail rules may contain multiple chemicals:
#
#       Ametryn + MCPA + BB5
#
#    with corresponding rates:
#
#       2 + 2 + 0.09
#
#    and units:
#
#       L/ha + L/ha + L/ha
#
# 5. Planting, harvesting and seedcane-cutting dates are read
#    from the same agricultural source files used elsewhere
#    in the system.
#
# 6. Seedcane Cutting uses Source Field.
#
# 7. Programme status is based on actual application data,
#    not chemical requests or stores issues.
#
# ==========================================================


# ==========================================================
# HERBICIDE RULES
# ==========================================================

HERBICIDE_RULES_FILE = (
    "data/herbicide_rules.xlsx"
)

HERBICIDE_RULE_COLUMNS = [
    "Rule ID",
    "Season",
    "Trigger",
    "Crop Situation",
    "Application Stage",
    "Application Type",
    "Chemical",
    "Target Weed",
    "Timing Type",
    "Timing Value",
    "Timing Unit",
    "Rate",
    "Rate Unit",
    "Mandatory",
    "Effective From",
    "Effective To",
    "Active",
    "Notes"
]

# ==========================================================
# APPLICATION STAGES
# ==========================================================

HERBICIDE_APPLICATION_STAGES = [

    "Pre-Emergent",

    "Early-Post Emergent",

    "Post-Emergent"

]

# ==========================================================
# APPLICATION TYPES
# ==========================================================

HERBICIDE_APPLICATION_TYPES = [

    "Standard Cocktail",

    "Selective Post"

]

# ==========================================================
# TRIGGERS
# ==========================================================

HERBICIDE_TRIGGERS = [

    "Planting",

    "Harvesting",

    "Seedcane Cutting",

    "Seasonal"

]

# ==========================================================
# CROP SITUATIONS
# ==========================================================

HERBICIDE_CROP_SITUATIONS = [

    "Irrigated",

    "Rain-fed",

    "All"

]

# ==========================================================
# TIMING TYPES
# ==========================================================

HERBICIDE_TIMING_TYPES = [

    "Days After Trigger",

    "Calendar Date",

    "Month",

    "Seasonal Condition"

]

# ==========================================================
# TIMING UNITS
# ==========================================================

HERBICIDE_TIMING_UNITS = [

    "Days",

    "Date",

    "Month",

    "Condition"

]

# ==========================================================
# RATE UNITS
# ==========================================================

HERBICIDE_RATE_UNITS = [

    "L/ha",

    "kg/ha",

    "g/ha"

]

# ==========================================================
# MANDATORY OPTIONS
# ==========================================================

HERBICIDE_MANDATORY_OPTIONS = [

    "Yes",

    "No"

]

# ==========================================================
# TARGET WEEDS
# ==========================================================

HERBICIDE_TARGET_WEEDS = [

    "General Weeds",

    "Water Grass",

    "Creepers",

    "Broadleaf Weeds",

    "Other"

]

# ==========================================================
# HERBICIDE CHEMICAL CATALOGUE
# ==========================================================
#
# IMPORTANT:
#
# THIS IS THE ONLY HERBICIDE CHEMICAL CATALOGUE.
#
# File:
#
#     data/herbicide_chemical_catalogue.xlsx
#
# Rates must NOT be duplicated in this module.
#
# ==========================================================

HERBICIDE_CATALOGUE_FILE = (
    "data/herbicide_chemical_catalogue.xlsx"
)

HERBICIDE_CATALOGUE_COLUMNS = [

    "Season",

    "Chemical",

    "Rate",

    "Rate Unit",

    "Active",

    "Notes"

]


# ==========================================================
# LOAD HERBICIDE CHEMICAL CATALOGUE
# ==========================================================

def load_herbicide_catalogue():
    """
    Load the herbicide chemical catalogue.

    SINGLE SOURCE OF TRUTH for:

        Chemical
        Rate
        Rate Unit
        Season
        Active
        Notes

    File:
        data/herbicide_chemical_catalogue.xlsx

    Catalogue rates are individual chemical rates.

    Examples:

        Ametryn = 2
        MCPA    = 2.5
        BB5     = 0.09

    Cocktail formatting is handled later by
    the herbicide rules.
    """

    columns = [
        "Season",
        "Chemical",
        "Rate",
        "Rate Unit",
        "Active",
        "Notes"
    ]

    # ------------------------------------------------------
    # FILE CHECK
    # ------------------------------------------------------

    if not os.path.exists(
        HERBICIDE_CATALOGUE_FILE
    ):

        print(
            "[HERBICIDE CATALOGUE] "
            f"File not found: {HERBICIDE_CATALOGUE_FILE}"
        )

        return pd.DataFrame(
            columns=columns
        )

    # ------------------------------------------------------
    # READ EXCEL
    # ------------------------------------------------------

    try:

        df = pd.read_excel(
            HERBICIDE_CATALOGUE_FILE,
            engine="openpyxl"
        )

    except Exception as e:

        print(
            "[HERBICIDE CATALOGUE] "
            f"Error loading catalogue: {e}"
        )

        return pd.DataFrame(
            columns=columns
        )

    # ------------------------------------------------------
    # EMPTY FILE
    # ------------------------------------------------------

    if df.empty:

        print(
            "[HERBICIDE CATALOGUE] "
            "Catalogue file contains no rows."
        )

        return pd.DataFrame(
            columns=columns
        )

    # ------------------------------------------------------
    # CLEAN COLUMN NAMES
    # ------------------------------------------------------

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # ENSURE ALL REQUIRED COLUMNS EXIST
    # ------------------------------------------------------

    for column in columns:

        if column not in df.columns:

            df[column] = ""

    # ------------------------------------------------------
    # KEEP STANDARD ORDER
    # ------------------------------------------------------

    df = df[
        columns
    ].copy()

    # ------------------------------------------------------
    # CLEAN TEXT COLUMNS
    # ------------------------------------------------------

    for column in [
        "Season",
        "Chemical",
        "Rate Unit",
        "Active",
        "Notes"
    ]:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ------------------------------------------------------
    # NORMALISE SEASON
    # ------------------------------------------------------

    df["Season"] = (
        df["Season"]
        .str.replace(
            " ",
            "",
            regex=False
        )
    )

    # ------------------------------------------------------
    # NORMALISE ACTIVE
    # ------------------------------------------------------

    df["Active"] = (
        df["Active"]
        .str.upper()
        .replace(
            {
                "TRUE": "YES",
                "1": "YES",
                "Y": "YES",

                "FALSE": "NO",
                "0": "NO",
                "N": "NO"
            }
        )
    )

    # Blank / unexpected Active values
    # default to YES.
    df.loc[
        ~df["Active"].isin(
            ["YES", "NO"]
        ),
        "Active"
    ] = "YES"

    # ------------------------------------------------------
    # NUMERIC RATE
    # ------------------------------------------------------

    df["Rate"] = pd.to_numeric(
        df["Rate"],
        errors="coerce"
    )

    # ------------------------------------------------------
    # REMOVE COMPLETELY EMPTY CHEMICAL ROWS
    # ------------------------------------------------------

    df = df[
        df["Chemical"].str.strip() != ""
    ].copy()

    return df


# ==========================================================
# SAVE HERBICIDE CHEMICAL CATALOGUE
# ==========================================================

def save_herbicide_catalogue(df):
    """
    Save the single herbicide chemical catalogue.
    """

    os.makedirs(
        os.path.dirname(
            HERBICIDE_CATALOGUE_FILE
        ),
        exist_ok=True
    )

    for column in HERBICIDE_CATALOGUE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df = df[
        HERBICIDE_CATALOGUE_COLUMNS
    ].copy()

    df.to_excel(
        HERBICIDE_CATALOGUE_FILE,
        index=False
    )


# ==========================================================
# LOAD HERBICIDE RULES
# ==========================================================

def load_herbicide_rules():
    """
    Load herbicide rules from Excel.

    Supports:

        - Standard Cocktail
        - Selective Post
        - Multiple chemicals
        - Target Weed
        - Mandatory
        - Season
        - Timing rules

    IMPORTANT:

    Rule rates are NOT recalculated from a manual rate table.

    They are copied from the chemical catalogue when a rule
    is created or updated.

    Cocktail rates are intentionally stored as TEXT.

    Example:

        Chemical:
            Ametryn + MCPA + BB5

        Rate:
            2 + 2.5 + 0.09

        Rate Unit:
            L/ha + L/ha + L/ha
    """

    if not os.path.exists(
            HERBICIDE_RULES_FILE
    ):
        return pd.DataFrame(
            columns=HERBICIDE_RULE_COLUMNS
        )

    try:

        df = pd.read_excel(
            HERBICIDE_RULES_FILE
        )

    except Exception as e:

        print(
            f"Error loading herbicide rules: {e}"
        )

        return pd.DataFrame(
            columns=HERBICIDE_RULE_COLUMNS
        )

    # ------------------------------------------------------
    # ENSURE ALL COLUMNS EXIST
    # ------------------------------------------------------

    for column in HERBICIDE_RULE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    # ------------------------------------------------------
    # STANDARD COLUMN ORDER
    # ------------------------------------------------------

    df = df[
        HERBICIDE_RULE_COLUMNS
    ].copy()

    # ------------------------------------------------------
    # TEXT COLUMNS
    # ------------------------------------------------------

    text_columns = [

        "Rule ID",

        "Season",

        "Trigger",

        "Crop Situation",

        "Application Stage",

        "Application Type",

        "Chemical",

        "Target Weed",

        "Timing Type",

        "Timing Unit",

        "Rate",

        "Rate Unit",

        "Effective From",

        "Effective To",

        "Mandatory",

        "Active",

        "Notes"

    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ------------------------------------------------------
    # DEFAULT APPLICATION TYPE
    # ------------------------------------------------------

    df.loc[
        df["Application Type"] == "",
        "Application Type"
    ] = "Standard Cocktail"

    # ------------------------------------------------------
    # NORMALISE APPLICATION TYPE
    # ------------------------------------------------------

    df["Application Type"] = (
        df["Application Type"]
        .replace(
            {
                "STANDARD COCKTAIL":
                    "Standard Cocktail",

                "STANDARD":
                    "Standard Cocktail",

                "COCKTAIL":
                    "Standard Cocktail",

                "SELECTIVE":
                    "Selective Post",

                "SELECTIVE POST":
                    "Selective Post"
            }
        )
    )

    df.loc[
        ~df["Application Type"].isin(
            HERBICIDE_APPLICATION_TYPES
        ),
        "Application Type"
    ] = "Standard Cocktail"

    # ------------------------------------------------------
    # DEFAULT TARGET WEED
    # ------------------------------------------------------

    df.loc[
        df["Target Weed"] == "",
        "Target Weed"
    ] = "General Weeds"

    # ------------------------------------------------------
    # NORMALISE MANDATORY
    # ------------------------------------------------------

    df["Mandatory"] = (
        df["Mandatory"]
        .str.upper()
        .replace(
            {
                "TRUE": "YES",
                "1": "YES",
                "Y": "YES",

                "FALSE": "NO",
                "0": "NO",
                "N": "NO"
            }
        )
    )

    df.loc[
        ~df["Mandatory"].isin(
            ["YES", "NO"]
        ),
        "Mandatory"
    ] = "NO"

    # ------------------------------------------------------
    # NORMALISE ACTIVE
    # ------------------------------------------------------

    df["Active"] = (
        df["Active"]
        .str.upper()
        .replace(
            {
                "TRUE": "YES",
                "1": "YES",
                "Y": "YES",

                "FALSE": "NO",
                "0": "NO",
                "N": "NO"
            }
        )
    )

    df.loc[
        ~df["Active"].isin(
            ["YES", "NO"]
        ),
        "Active"
    ] = "YES"

    # ------------------------------------------------------
    # TIMING VALUE
    # ------------------------------------------------------
    #
    # Timing Value is numeric for:
    #
    #     Days After Trigger
    #     Month
    #
    # Calendar Date may be represented as text.
    #
    # Therefore we DO NOT globally convert Timing Value
    # to numeric.
    #
    # ------------------------------------------------------

    df["Timing Value"] = (
        df["Timing Value"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # DO NOT CONVERT RATE TO NUMERIC.
    #
    # Cocktail rules contain values such as:
    #
    #     2 + 2.5 + 0.09
    #
    # ------------------------------------------------------

    df["Rate"] = (
        df["Rate"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return df


# ==========================================================
# SAVE HERBICIDE RULES
# ==========================================================

def save_herbicide_rules(df):
    """
    Save herbicide rules using the current standard structure.

    IMPORTANT:
    Rate remains TEXT because cocktail rules may contain
    multiple rates.
    """

    os.makedirs(
        os.path.dirname(
            HERBICIDE_RULES_FILE
        ),
        exist_ok=True
    )

    # ------------------------------------------------------
    # ENSURE COLUMNS
    # ------------------------------------------------------

    for column in HERBICIDE_RULE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df = df[
        HERBICIDE_RULE_COLUMNS
    ].copy()

    # ------------------------------------------------------
    # TEXT CLEANING
    # ------------------------------------------------------

    for column in HERBICIDE_RULE_COLUMNS:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ------------------------------------------------------
    # APPLICATION TYPE
    # ------------------------------------------------------

    df.loc[
        df["Application Type"] == "",
        "Application Type"
    ] = "Standard Cocktail"

    # ------------------------------------------------------
    # TARGET WEED
    # ------------------------------------------------------

    df.loc[
        df["Target Weed"] == "",
        "Target Weed"
    ] = "General Weeds"

    # ------------------------------------------------------
    # MANDATORY
    # ------------------------------------------------------

    df["Mandatory"] = (
        df["Mandatory"]
        .str.upper()
        .replace(
            {
                "TRUE": "YES",
                "1": "YES",
                "Y": "YES",

                "FALSE": "NO",
                "0": "NO",
                "N": "NO"
            }
        )
    )

    df.loc[
        ~df["Mandatory"].isin(
            ["YES", "NO"]
        ),
        "Mandatory"
    ] = "NO"

    # ------------------------------------------------------
    # ACTIVE
    # ------------------------------------------------------

    df["Active"] = (
        df["Active"]
        .str.upper()
        .replace(
            {
                "TRUE": "YES",
                "1": "YES",
                "Y": "YES",

                "FALSE": "NO",
                "0": "NO",
                "N": "NO"
            }
        )
    )

    df.loc[
        ~df["Active"].isin(
            ["YES", "NO"]
        ),
        "Active"
    ] = "YES"

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------

    df.to_excel(
        HERBICIDE_RULES_FILE,
        index=False
    )


# ==========================================================
# GENERATE HERBICIDE RULE ID
# ==========================================================

def generate_herbicide_rule_id(df):
    if (
            df is None
            or df.empty
            or "Rule ID" not in df.columns
    ):
        return "HR001"

    numbers = []

    for value in df["Rule ID"].astype(str):

        value = value.strip().upper()

        if value.startswith("HR"):

            try:

                numbers.append(
                    int(value[2:])
                )

            except ValueError:

                pass

    if not numbers:
        return "HR001"

    return (
        f"HR{max(numbers) + 1:03d}"
    )


# ==========================================================
# COPY HERBICIDE RULES FROM PREVIOUS SEASON
# ==========================================================

def copy_herbicide_rules_from_previous_season(
        current_season
):
    df = load_herbicide_rules()

    if df.empty:
        return 0

    current_season = str(
        current_season or ""
    ).strip()

    if not current_season:
        return 0

    # ------------------------------------------------------
    # DO NOT COPY IF CURRENT SEASON ALREADY EXISTS
    # ------------------------------------------------------

    if (
            df["Season"]
                    .astype(str)
                    .str.strip()
                    .eq(current_season)
                    .any()
    ):
        return 0

    # ------------------------------------------------------
    # DETERMINE PREVIOUS SEASON
    #
    # 2026/27 -> 2025/26
    # ------------------------------------------------------

    try:

        start_year = int(
            current_season[:4]
        )

        previous_season = (
            f"{start_year - 1}/{str(start_year)[-2:]}"
        )

    except Exception:

        return 0

    previous = df[
        df["Season"]
        .astype(str)
        .str.strip()
        == previous_season
        ].copy()

    if previous.empty:
        return 0

    # ------------------------------------------------------
    # FIND NEXT RULE ID
    # ------------------------------------------------------

    next_rule_number = 1

    existing_ids = []

    for value in df["Rule ID"].astype(str):

        value = value.strip().upper()

        if value.startswith("HR"):

            try:

                existing_ids.append(
                    int(value[2:])
                )

            except ValueError:

                pass

    if existing_ids:
        next_rule_number = (
                max(existing_ids) + 1
        )

    copied = []

    for _, row in previous.iterrows():
        new_row = row.copy()

        new_row["Rule ID"] = (
            f"HR{next_rule_number:03d}"
        )

        new_row["Season"] = current_season

        next_rule_number += 1

        copied.append(
            new_row
        )

    if not copied:
        return 0

    copied_df = pd.DataFrame(
        copied
    )

    df = pd.concat(
        [
            df,
            copied_df
        ],
        ignore_index=True
    )

    save_herbicide_rules(
        df
    )

    return len(
        copied_df
    )


# ==========================================================
# HERBICIDE TRIGGER-DATE INTEGRATION
# ==========================================================

PLANTING_RECORDS_FILE = (
    "data/planting_records.xlsx"
)

HARVESTING_RECORDS_FILE = (
    "data/harvesting_records.xlsx"
)

SEEDCANE_CUTTING_FILE = (
    "data/seedcane_cutting.xlsx"
)


# ==========================================================
# LOAD HERBICIDE ACTIVITY EVENTS
# ==========================================================

def load_herbicide_activity_events(season):
    """
    Load agricultural activity events used by the
    herbicide programme.

    Sources:

        planting_records.xlsx
        harvesting_records.xlsx
        seedcane_cutting.xlsx

    Seedcane Cutting uses:
        Source Field

    The loader is intentionally tolerant of common date
    column names so that the herbicide module does not
    depend on one exact spreadsheet heading.
    """

    events = []

    # ======================================================
    # NORMALISE SEASON
    # ======================================================

    season_text = str(
        season or ""
    ).strip().replace(
        " ",
        ""
    )

    # ======================================================
    # HELPER: FIND FIELD COLUMN
    # ======================================================

    def find_field_column(df, candidates):

        for column in candidates:

            if column in df.columns:
                return column

        return None

    # ======================================================
    # HELPER: FIND DATE COLUMN
    # ======================================================

    def find_date_column(df, candidates):

        for column in candidates:

            if column in df.columns:
                return column

        return None

    # ======================================================
    # HELPER: ADD EVENTS
    # ======================================================

    def add_events_from_file(
            file_path,
            field_candidates,
            date_candidates,
            event_type,
            source
    ):

        if not os.path.exists(
            file_path
        ):
            return

        try:

            df = pd.read_excel(
                file_path,
                engine="openpyxl"
            )

        except Exception as e:

            print(
                f"[HERBICIDE EVENTS] "
                f"Error loading {file_path}: {e}"
            )

            return

        if df.empty:
            return

        # --------------------------------------------------
        # CLEAN COLUMN NAMES
        # --------------------------------------------------

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        field_column = find_field_column(
            df,
            field_candidates
        )

        date_column = find_date_column(
            df,
            date_candidates
        )

        if not field_column:

            print(
                f"[HERBICIDE EVENTS] "
                f"No field column found in {file_path}. "
                f"Available columns: {list(df.columns)}"
            )

            return

        if not date_column:

            print(
                f"[HERBICIDE EVENTS] "
                f"No date column found in {file_path}. "
                f"Available columns: {list(df.columns)}"
            )

            return

        # --------------------------------------------------
        # READ EVENTS
        # --------------------------------------------------

        for _, row in df.iterrows():

            field = str(
                row.get(
                    field_column,
                    ""
                )
            ).strip()

            date = pd.to_datetime(
                row.get(
                    date_column
                ),
                errors="coerce"
            )

            if not field:
                continue

            if pd.isna(date):
                continue

            events.append({

                "Field":
                    field,

                "Date":
                    date,

                "Event Type":
                    event_type,

                "Source":
                    source

            })

    # ======================================================
    # PLANTING
    # ======================================================

    add_events_from_file(

        PLANTING_RECORDS_FILE,

        [
            "Field",
            "Main Field",
            "Subfield"
        ],

        [
            "Date",
            "Planting Date",
            "Plant Date",
            "Planting_Date"
        ],

        "PLANT",

        "Planting"

    )

    # ======================================================
    # HARVESTING
    # ======================================================

    add_events_from_file(

        HARVESTING_RECORDS_FILE,

        [
            "Field",
            "Main Field",
            "Subfield"
        ],

        [
            "Date",
            "Harvest Date",
            "Harvesting Date",
            "Harvest_Date"
        ],

        "RATOON",

        "Harvesting"

    )

    # ======================================================
    # SEEDCANE CUTTING
    # ======================================================

    if os.path.exists(
        SEEDCANE_CUTTING_FILE
    ):

        try:

            df = pd.read_excel(
                SEEDCANE_CUTTING_FILE,
                engine="openpyxl"
            )

            if not df.empty:

                df.columns = (
                    df.columns
                    .astype(str)
                    .str.strip()
                )

                # IMPORTANT:
                #
                # Source Field is the field associated
                # with the seedcane cutting.

                field_column = None

                for column in [
                    "Source Field",
                    "Field",
                    "Main Field"
                ]:

                    if column in df.columns:
                        field_column = column
                        break

                date_column = None

                for column in [
                    "Date",
                    "Cutting Date",
                    "Cut Date"
                ]:

                    if column in df.columns:
                        date_column = column
                        break

                if field_column and date_column:

                    for _, row in df.iterrows():

                        source_field = str(
                            row.get(
                                field_column,
                                ""
                            )
                        ).strip()

                        date = pd.to_datetime(
                            row.get(
                                date_column
                            ),
                            errors="coerce"
                        )

                        if not source_field:
                            continue

                        if pd.isna(date):
                            continue

                        events.append({

                            "Field":
                                source_field,

                            "Date":
                                date,

                            "Event Type":
                                "RATOON",

                            "Source":
                                "Seedcane Cutting"

                        })

                else:

                    print(
                        "[HERBICIDE EVENTS] "
                        "Seedcane cutting file does not "
                        "contain a recognised field/date "
                        "combination."
                    )

        except Exception as e:

            print(
                "[HERBICIDE EVENTS] "
                f"Error loading seedcane cutting: {e}"
            )

    # ======================================================
    # NO EVENTS
    # ======================================================

    if not events:

        print(
            "[HERBICIDE EVENTS] "
            f"No activity events found for {season}."
        )

        return pd.DataFrame(
            columns=[
                "Field",
                "Date",
                "Event Type",
                "Source"
            ]
        )

    events_df = pd.DataFrame(
        events
    )

    # ======================================================
    # NORMALISE DATES
    # ======================================================

    events_df["Date"] = pd.to_datetime(
        events_df["Date"],
        errors="coerce"
    )

    events_df = events_df[
        events_df["Date"].notna()
    ].copy()

    # ======================================================
    # LOAD SEASON DATES
    # ======================================================

    season_file = (
        "data/season_data.xlsx"
    )

    season_start = None
    season_end = None

    if os.path.exists(
        season_file
    ):

        try:

            season_df = pd.read_excel(
                season_file,
                engine="openpyxl"
            )

            season_df.columns = (
                season_df.columns
                .astype(str)
                .str.strip()
            )

            if all(
                column in season_df.columns

                for column in [
                    "Season Name",
                    "Start Date",
                    "End Date"
                ]
            ):

                season_names = (
                    season_df["Season Name"]
                    .astype(str)
                    .str.strip()
                    .str.replace(
                        " ",
                        "",
                        regex=False
                    )
                )

                match = season_df[
                    season_names
                    ==
                    season_text
                ]

                if not match.empty:

                    season_row = (
                        match.iloc[0]
                    )

                    season_start = pd.to_datetime(
                        season_row["Start Date"],
                        errors="coerce"
                    )

                    season_end = pd.to_datetime(
                        season_row["End Date"],
                        errors="coerce"
                    )

        except Exception as e:

            print(
                "[HERBICIDE EVENTS] "
                f"Error loading season dates: {e}"
            )

    # ======================================================
    # FILTER TO ACTIVE SEASON
    # ======================================================

    if (
        season_start is not None
        and pd.notna(season_start)
        and
        season_end is not None
        and pd.notna(season_end)
    ):

        events_df = events_df[
            (
                events_df["Date"]
                >=
                season_start
            )
            &
            (
                events_df["Date"]
                <=
                season_end
            )
        ].copy()

    # ======================================================
    # NORMALISE FIELD
    # ======================================================

    events_df["Field"] = (
        events_df["Field"]
        .astype(str)
        .str.strip()
    )

    # ======================================================
    # DIAGNOSTIC
    # ======================================================

    print(
        "[HERBICIDE EVENTS] "
        f"{len(events_df)} event(s) loaded "
        f"for season {season}."
    )

    if not events_df.empty:

        print(
            events_df[
                [
                    "Field",
                    "Date",
                    "Source"
                ]
            ].to_string(
                index=False
            )
        )

    return events_df

# ==========================================================
# GET HERBICIDE TRIGGER DATE
# ==========================================================

def get_herbicide_trigger_date(
        field,
        trigger,
        season,
        events_df=None
):
    """
    Find the latest trigger date for a field.

    Supported:

        Planting
        Harvesting
        Seedcane Cutting
    """

    field = str(
        field or ""
    ).strip()

    trigger = str(
        trigger or ""
    ).strip()

    if not field or not trigger:
        return None

    # ------------------------------------------------------
    # LOAD EVENTS
    # ------------------------------------------------------

    if events_df is None:

        events_df = (
            load_herbicide_activity_events(
                season
            )
        )

    if (
        events_df is None
        or events_df.empty
    ):
        return None

    # ------------------------------------------------------
    # SOURCE
    # ------------------------------------------------------

    source_map = {

        "Planting":
            "Planting",

        "Harvesting":
            "Harvesting",

        "Seedcane Cutting":
            "Seedcane Cutting"

    }

    source = source_map.get(
        trigger
    )

    if not source:
        return None

    # ------------------------------------------------------
    # MATCH FIELD
    # ------------------------------------------------------

    field_events = events_df[
        (
            events_df["Field"]
            .astype(str)
            .str.strip()
            .str.upper()
            ==
            field.upper()
        )
        &
        (
            events_df["Source"]
            .astype(str)
            .str.strip()
            .str.upper()
            ==
            source.upper()
        )
    ].copy()

    if field_events.empty:
        return None

    # ------------------------------------------------------
    # LATEST EVENT
    # ------------------------------------------------------

    field_events["Date"] = pd.to_datetime(
        field_events["Date"],
        errors="coerce"
    )

    field_events = field_events[
        field_events["Date"].notna()
    ].sort_values(
        "Date"
    )

    if field_events.empty:
        return None

    return pd.to_datetime(
        field_events.iloc[-1]["Date"],
        errors="coerce"
    )

# ==========================================================
# HERBICIDE PLANNED DATE
# ==========================================================

def calculate_herbicide_planned_date(
        trigger_date,
        timing_type,
        timing_value,
        season=None,
        field_situation=None
):
    """
    Calculate planned herbicide application date.

    Supported:

        Days After Trigger
        Calendar Date
        Month
        Seasonal Condition
    """

    timing_type = str(
        timing_type or ""
    ).strip()

    timing_type_normalised = (
        timing_type
        .upper()
        .replace(
            "-",
            " "
        )
    )

    # ======================================================
    # DAYS AFTER TRIGGER
    # ======================================================

    if timing_type_normalised == (
        "DAYS AFTER TRIGGER"
    ):

        if (
            trigger_date is None
            or pd.isna(trigger_date)
        ):
            return None

        try:

            days = int(
                float(
                    timing_value
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return None

        return (
            pd.to_datetime(
                trigger_date
            )
            +
            timedelta(
                days=days
            )
        )

    # ======================================================
    # CALENDAR DATE
    # ======================================================

    if timing_type_normalised == (
        "CALENDAR DATE"
    ):

        if (
            timing_value is None
            or
            str(
                timing_value
            ).strip() == ""
        ):
            return None

        date_value = pd.to_datetime(
            timing_value,
            errors="coerce"
        )

        if pd.isna(date_value):
            return None

        return date_value

    # ======================================================
    # MONTH
    # ======================================================

    if timing_type_normalised == "MONTH":

        if not season:
            return None

        try:

            month = int(
                float(
                    timing_value
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return None

        if month < 1 or month > 12:
            return None

        try:

            start_year = int(
                str(
                    season
                ).strip()[:4]
            )

            # DCGL season:
            #
            # 2026/27
            #
            # Apr 2026 - Mar 2027
            #
            if month <= 3:
                year = start_year + 1
            else:
                year = start_year

            return pd.Timestamp(
                year=year,
                month=month,
                day=1
            )

        except Exception:

            return None

    # ======================================================
    # SEASONAL CONDITION
    # ======================================================

    if timing_type_normalised == (
        "SEASONAL CONDITION"
    ):

        # A seasonal condition requires an actual
        # agricultural/weather decision.
        #
        # Do not invent a date.

        return None

    return None


# ==========================================================
# HERBICIDE RULE CHEMICAL VALIDATION
# ==========================================================

def get_rule_chemicals_from_catalogue(
        chemical_names,
        season,
        catalogue_df=None
):
    """
    Validate rule chemicals against the active season
    chemical catalogue.

    Returns:

        [
            {
                "Chemical": "...",
                "Rate": ...,
                "Rate Unit": "..."
            }
        ]

    The catalogue is the authority for rates.
    """

    if catalogue_df is None:
        catalogue_df = (
            load_herbicide_catalogue()
        )

    if (
            catalogue_df is None
            or catalogue_df.empty
    ):
        return []

    results = []

    for chemical in chemical_names:

        chemical = str(
            chemical or ""
        ).strip()

        if not chemical:
            continue

        matches = catalogue_df[

            (
                    catalogue_df["Season"]
                    .astype(str)
                    .str.strip()
                    ==
                    str(season).strip()
            )

            &

            (
                    catalogue_df["Chemical"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    ==
                    chemical.upper()
            )

            &

            (
                    catalogue_df["Active"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    ==
                    "YES"
            )

            ]

        if matches.empty:
            return None

        results.append(
            matches.iloc[0]
        )

    return results


# ==========================================================
# BUILD RULE RATE FROM CATALOGUE
# ==========================================================

def build_herbicide_rule_rate(
        catalogue_entries
):
    """
    Build the rate and rate-unit strings from catalogue rows.

    Single:

        Rate:
            2

        Rate Unit:
            L/ha

    Cocktail:

        Rate:
            2 + 2.5 + 0.09

        Rate Unit:
            L/ha + L/ha + L/ha
    """

    if not catalogue_entries:
        return "", ""

    rates = []
    units = []

    for entry in catalogue_entries:

        rate = entry.get(
            "Rate",
            ""
        )

        if pd.isna(rate):
            rate = ""

        rate_text = str(
            rate
        ).strip()

        units_text = str(
            entry.get(
                "Rate Unit",
                ""
            )
        ).strip()

        rates.append(
            rate_text
        )

        units.append(
            units_text
        )

    return (
        " + ".join(rates),
        " + ".join(units)
    )


# ==========================================================
# HERBICIDE RULES ROUTE
# ==========================================================

@activity_bp.route(
    "/agriculture/herbicide-rules",
    methods=["GET", "POST"]
)
def herbicide_rules():
    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    # ======================================================
    # ROLE CONTROL
    # ======================================================

    allowed_roles = [

        "Admin",

        "Manager",

        "Agriculture Manager"

    ]

    if session.get("role") not in allowed_roles:
        flash(
            "You do not have permission to manage herbicide rules.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide"
            )
        )

    # ======================================================
    # LOAD RULES
    # ======================================================

    df = load_herbicide_rules()

    # ======================================================
    # LOAD SINGLE CHEMICAL CATALOGUE
    # ======================================================

    chemical_df = (
        load_herbicide_catalogue()
    )

    # ======================================================
    # POST ACTIONS
    # ======================================================

    if request.method == "POST":

        action = (
            request.form.get(
                "action",
                "add"
            )
            .strip()
            .lower()
        )

        # ==================================================
        # ADD RULE
        # ==================================================

        if action == "add":

            rule_id = (
                generate_herbicide_rule_id(
                    df
                )
            )

            # ------------------------------------------------
            # SELECT CHEMICALS
            # ------------------------------------------------

            selected_chemicals = [

                str(item).strip()

                for item in request.form.getlist(
                    "Chemical"
                )

                if str(item).strip()

            ]

            if not selected_chemicals:
                flash(
                    "At least one chemical must be selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # APPLICATION TYPE
            # ------------------------------------------------

            application_type = (
                request.form.get(
                    "Application Type",
                    "Standard Cocktail"
                )
                .strip()
            )

            # ------------------------------------------------
            # NON-COCKTAIL = ONE CHEMICAL ONLY
            # ------------------------------------------------

            if (
                    application_type.upper()
                    != "STANDARD COCKTAIL"
                    and
                    len(selected_chemicals) > 1
            ):
                flash(
                    "Only one chemical can be selected "
                    "for a non-cocktail herbicide application.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # VALIDATE CHEMICALS
            # ------------------------------------------------

            catalogue_entries = (
                get_rule_chemicals_from_catalogue(
                    selected_chemicals,
                    season,
                    chemical_df
                )
            )

            if catalogue_entries is None:
                invalid_names = ", ".join(
                    selected_chemicals
                )

                flash(
                    f"One or more selected chemicals are "
                    f"not active in the {season} catalogue: "
                    f"{invalid_names}",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # BUILD RATE FROM CATALOGUE
            # ------------------------------------------------

            rate_value, rate_unit_value = (
                build_herbicide_rule_rate(
                    catalogue_entries
                )
            )

            chemical_value = " + ".join(
                selected_chemicals
            )

            # ------------------------------------------------
            # RULE SEASON
            #
            # Always use the active season.
            # ------------------------------------------------

            data = {

                "Rule ID":
                    rule_id,

                "Season":
                    season,

                "Trigger":
                    request.form.get(
                        "Trigger",
                        ""
                    ),

                "Crop Situation":
                    request.form.get(
                        "Crop Situation",
                        ""
                    ),

                "Application Stage":
                    request.form.get(
                        "Application Stage",
                        ""
                    ),

                "Application Type":
                    application_type,

                "Chemical":
                    chemical_value,

                "Target Weed":
                    request.form.get(
                        "Target Weed",
                        "General Weeds"
                    ),

                "Timing Type":
                    request.form.get(
                        "Timing Type",
                        ""
                    ),

                "Timing Value":
                    request.form.get(
                        "Timing Value",
                        ""
                    ),

                "Timing Unit":
                    request.form.get(
                        "Timing Unit",
                        ""
                    ),

                "Rate":
                    rate_value,

                "Rate Unit":
                    rate_unit_value,

                "Mandatory":
                    request.form.get(
                        "Mandatory",
                        "NO"
                    ),

                "Effective From":
                    request.form.get(
                        "Effective From",
                        ""
                    ),

                "Effective To":
                    request.form.get(
                        "Effective To",
                        ""
                    ),

                "Active":
                    "YES",

                "Notes":
                    request.form.get(
                        "Notes",
                        ""
                    )

            }

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [data]
                    )
                ],
                ignore_index=True
            )

            save_herbicide_rules(
                df
            )

            flash(
                f"Herbicide rule {rule_id} added successfully "
                f"using {chemical_value} at "
                f"{rate_value} {rate_unit_value}.",
                "success"
            )

            return redirect(
                url_for(
                    "activities.herbicide_rules"
                )
            )


        # ==================================================
        # UPDATE RULE
        # ==================================================

        elif action == "update":

            rule_id = (
                request.form.get(
                    "Rule ID",
                    ""
                )
                .strip()
            )

            if (
                    not rule_id
                    or df.empty
            ):
                flash(
                    "Invalid herbicide rule.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            matches = (
                    df["Rule ID"]
                    .astype(str)
                    .str.strip()
                    ==
                    rule_id
            )

            if not matches.any():
                flash(
                    "Herbicide rule not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            index = df.index[
                matches
            ][0]

            # ------------------------------------------------
            # UPDATE EDITABLE FIELDS
            # ------------------------------------------------

            editable_columns = [

                "Trigger",

                "Crop Situation",

                "Application Stage",

                "Application Type",

                "Chemical",

                "Target Weed",

                "Timing Type",

                "Timing Value",

                "Timing Unit",

                "Mandatory",

                "Effective From",

                "Effective To",

                "Notes"

            ]

            for column in editable_columns:
                df.at[
                    index,
                    column
                ] = request.form.get(
                    column,
                    ""
                )

            # ------------------------------------------------
            # RULE ALWAYS REMAINS IN ACTIVE SEASON
            # ------------------------------------------------

            df.at[
                index,
                "Season"
            ] = season

            # ------------------------------------------------
            # APPLICATION TYPE
            # ------------------------------------------------

            application_type = str(
                df.at[
                    index,
                    "Application Type"
                ]
            ).strip()

            # ------------------------------------------------
            # SELECT CHEMICALS FROM UPDATE FORM
            # ------------------------------------------------

            selected_chemicals = [

                str(item).strip()

                for item in request.form.getlist(
                    "Chemical"
                )

                if str(item).strip()

            ]

            # ------------------------------------------------
            # FALLBACK FOR SINGLE VALUE
            # ------------------------------------------------

            if not selected_chemicals:

                submitted_chemical = (
                    request.form.get(
                        "Chemical",
                        ""
                    )
                    .strip()
                )

                if submitted_chemical:
                    selected_chemicals = [

                        item.strip()

                        for item in submitted_chemical.split("+")

                        if item.strip()

                    ]

            if not selected_chemicals:
                flash(
                    "At least one chemical must be selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # NON-COCKTAIL VALIDATION
            # ------------------------------------------------

            if (
                    application_type.upper()
                    != "STANDARD COCKTAIL"
                    and
                    len(selected_chemicals) > 1
            ):
                flash(
                    "Only one chemical is allowed for "
                    "a non-cocktail application.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # VALIDATE AGAINST CURRENT CATALOGUE
            # ------------------------------------------------

            catalogue_entries = (
                get_rule_chemicals_from_catalogue(
                    selected_chemicals,
                    season,
                    chemical_df
                )
            )

            if catalogue_entries is None:
                flash(
                    "One or more chemicals are not active "
                    f"in the {season} chemical catalogue.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_rules"
                    )
                )

            # ------------------------------------------------
            # REBUILD CHEMICAL
            # ------------------------------------------------

            df.at[
                index,
                "Chemical"
            ] = " + ".join(
                selected_chemicals
            )

            # ------------------------------------------------
            # REBUILD RATE FROM CATALOGUE
            # ------------------------------------------------

            rate_value, rate_unit_value = (
                build_herbicide_rule_rate(
                    catalogue_entries
                )
            )

            df.at[
                index,
                "Rate"
            ] = rate_value

            df.at[
                index,
                "Rate Unit"
            ] = rate_unit_value

            # ------------------------------------------------
            # SAVE
            # ------------------------------------------------

            save_herbicide_rules(
                df
            )

            flash(
                f"Herbicide rule {rule_id} updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "activities.herbicide_rules"
                )
            )


        # ==================================================
        # TOGGLE RULE
        # ==================================================

        elif action == "toggle":

            rule_id = (
                request.form.get(
                    "Rule ID",
                    ""
                )
                .strip()
            )

            matches = (
                    df["Rule ID"]
                    .astype(str)
                    .str.strip()
                    ==
                    rule_id
            )

            if matches.any():

                index = df.index[
                    matches
                ][0]

                current_status = str(
                    df.at[
                        index,
                        "Active"
                    ]
                ).strip().upper()

                new_status = (
                    "NO"
                    if current_status == "YES"
                    else "YES"
                )

                df.at[
                    index,
                    "Active"
                ] = new_status

                save_herbicide_rules(
                    df
                )

                flash(
                    f"Rule {rule_id} is now "
                    f"{'active' if new_status == 'YES' else 'inactive'}.",
                    "success"
                )


            else:

                flash(
                    "Herbicide rule not found.",
                    "warning"
                )

            return redirect(
                url_for(
                    "activities.herbicide_rules"
                )
            )


        # ==================================================
        # COPY PREVIOUS SEASON
        # ==================================================

        elif action == "copy_previous":

            copied_count = (
                copy_herbicide_rules_from_previous_season(
                    season
                )
            )

            if copied_count > 0:

                flash(
                    f"{copied_count} herbicide rule(s) "
                    f"copied into season {season}.",
                    "success"
                )

            else:

                flash(
                    "No previous-season rules were available "
                    "to copy, or rules already exist for this season.",
                    "warning"
                )

            return redirect(
                url_for(
                    "activities.herbicide_rules"
                )
            )

    # ======================================================
    # CURRENT SEASON RULES
    # ======================================================

    current_rules = df[
        df["Season"]
        .astype(str)
        .str.strip()
        ==
        str(season).strip()
        ].copy()

    # ======================================================
    # SORT RULES
    # ======================================================

    stage_order = {

        "PRE-EMERGENT":
            1,

        "EARLY-POST EMERGENT":
            2,

        "POST-EMERGENT":
            3

    }

    current_rules[
        "_StageOrder"
    ] = (
        current_rules[
            "Application Stage"
        ]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(stage_order)
        .fillna(99)
    )

    current_rules = (
        current_rules
        .sort_values(
            [
                "Trigger",
                "Crop Situation",
                "_StageOrder",
                "Application Type",
                "Chemical"
            ]
        )
        .drop(
            columns=[
                "_StageOrder"
            ]
        )
    )

    # ======================================================
    # ACTIVE SEASON CATALOGUE
    # ======================================================

    season_chemicals = chemical_df[
        chemical_df["Season"]
        .astype(str)
        .str.strip()
        ==
        str(season).strip()
        ].copy()

    season_chemicals = (
        season_chemicals
        .sort_values(
            [
                "Active",
                "Chemical"
            ],
            ascending=[
                False,
                True
            ]
        )
    )

    # ======================================================
    # ACTIVE CHEMICALS
    # ======================================================

    active_chemicals = season_chemicals[
        season_chemicals["Active"]
        .astype(str)
        .str.strip()
        .str.upper()
        ==
        "YES"
        ].copy()

    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "agriculture/herbicide_rules.html",

        season=season,

        rules=current_rules.to_dict(
            orient="records"
        ),

        triggers=HERBICIDE_TRIGGERS,

        crop_situations=(
            HERBICIDE_CROP_SITUATIONS
        ),

        application_stages=(
            HERBICIDE_APPLICATION_STAGES
        ),

        application_types=(
            HERBICIDE_APPLICATION_TYPES
        ),

        timing_types=(
            HERBICIDE_TIMING_TYPES
        ),

        chemicals=active_chemicals[
            "Chemical"
        ].tolist(),

        target_weeds=(
            HERBICIDE_TARGET_WEEDS
        ),

        mandatory_options=(
            HERBICIDE_MANDATORY_OPTIONS
        ),

        rate_units=(
            HERBICIDE_RATE_UNITS
        )
    )


# ==========================================================
# HERBICIDE SCHEDULE
# ==========================================================

HERBICIDE_SCHEDULE_FILE = (
    "data/herbicide_schedule.xlsx"
)

HERBICIDE_SCHEDULE_COLUMNS = [

    "Programme ID",

    "Season",

    "Field",

    "Crop Type",

    "Crop Situation",

    "Application Stage",

    "Chemical",

    "Planned Date",

    "Rate",

    "Rate Unit",

    "Area (ha)",

    "Planned Quantity",

    "Quantity Unit",

    "Trigger",

    "Trigger Date",

    "Status",

    "Actual Date",

    "Actual Quantity",

    "Notes"

]

# ==========================================================
# HERBICIDE APPLICATION CHEMICAL COLUMNS
# ==========================================================

HERBICIDE_APPLICATION_CHEMICAL_COLUMNS = [
    "MSMA",
    "MCPA",
    "Ametryn",
    "Altrazine",
    "Servian WP",
    "Round-Up",
    "Dual Magnum",
    "Sprint",
    "Garlon",
    "Acetochlor",
    "Metolachlor",
    "BB5"
]


# ==========================================================
# NORMALIZE HERBICIDE NAME
# ==========================================================

def normalize_herbicide_name(value):
    """
    Normalize a herbicide name for reliable matching.

    Examples:

        'Ametryn'       -> 'ametryn'
        ' Ametryn '     -> 'ametryn'
        'Round-Up'      -> 'round-up'
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("–", "-")
        .replace("—", "-")
    )


# ==========================================================
# GET CHEMICALS FROM PROGRAMME ENTRY
# ==========================================================

def get_programme_chemicals(chemical_text):
    """
    Convert a programme chemical string into a normalized
    list.

    Examples:

        Ametryn
            -> ['ametryn']

        Ametryn + MCPA
            -> ['ametryn', 'mcpa']

        Ametryn + MCPA + Zinc
            -> ['ametryn', 'mcpa', 'zinc']
    """

    if chemical_text is None:
        return []

    chemicals = []

    for chemical in str(
        chemical_text
    ).split("+"):

        normalized = normalize_herbicide_name(
            chemical
        )

        if normalized:
            chemicals.append(
                normalized
            )

    return chemicals


# ==========================================================
# GET ACTUAL CHEMICALS FROM APPLICATION RECORD
# ==========================================================

def get_application_chemicals(record):
    """
    Read the individual chemical columns from an actual
    herbicide application record.

    Only chemicals with a non-zero/non-empty quantity are
    considered applied.

    Returns:

        {
            'ametryn': '6',
            'mcpa': '2'
        }
    """

    chemicals = {}

    for chemical in (
        HERBICIDE_APPLICATION_CHEMICAL_COLUMNS
    ):

        value = record.get(
            chemical,
            ""
        )

        if pd.isna(value):
            continue

        value_text = str(
            value
        ).strip()

        if not value_text:
            continue

        # --------------------------------------------------
        # Ignore zero quantities
        # --------------------------------------------------

        try:

            numeric_value = float(
                value_text
            )

            if numeric_value == 0:
                continue

        except (
            ValueError,
            TypeError
        ):

            # If the value is text rather than numeric,
            # retain it because it may contain a valid
            # application quantity.
            pass

        chemicals[
            normalize_herbicide_name(
                chemical
            )
        ] = value_text

    return chemicals


# ==========================================================
# BUILD ACTUAL QUANTITY FOR PROGRAMME ENTRY
# ==========================================================

def build_actual_quantity(
    programme_chemicals,
    application_chemicals
):
    """
    Build Actual Quantity in the same chemical order as
    the programme.

    Example:

        Programme:
            Ametryn + MCPA

        Application:
            Ametryn = 6
            MCPA = 2

        Result:
            6 + 2
    """

    quantities = []

    for chemical in programme_chemicals:

        quantity = application_chemicals.get(
            chemical
        )

        if quantity is None:
            return ""

        quantities.append(
            str(quantity).strip()
        )

    return " + ".join(
        quantities
    )


# ==========================================================
# FIND BEST PROGRAMME MATCH
# ==========================================================

def find_best_herbicide_programme_match(
    schedule_df,
    season,
    field,
    application_date,
    application_chemicals
):
    """
    Find the best unapplied programme row for an actual
    herbicide application.

    Matching is based on:

        1. Season
        2. Field
        3. Exact chemical combination
        4. Programme row must not already be applied

    The closest planned date to the actual application date
    is selected.

    Preference is given to planned dates on or before the
    actual application date.
    """

    if schedule_df.empty:
        return None

    season_text = str(
        season
    ).strip()

    field_text = str(
        field
    ).strip().lower()

    application_chemical_set = set(
        application_chemicals.keys()
    )

    if not application_chemical_set:
        return None

    candidates = []

    for index, row in schedule_df.iterrows():

        # --------------------------------------------------
        # Season
        # --------------------------------------------------

        row_season = str(
            row.get(
                "Season",
                ""
            )
        ).strip()

        if row_season != season_text:
            continue

        # --------------------------------------------------
        # Field
        # --------------------------------------------------

        row_field = str(
            row.get(
                "Field",
                ""
            )
        ).strip().lower()

        if row_field != field_text:
            continue

        # --------------------------------------------------
        # Ignore already applied programme rows
        # --------------------------------------------------

        existing_actual = pd.to_datetime(
            row.get(
                "Actual Date"
            ),
            errors="coerce"
        )

        if pd.notna(
            existing_actual
        ):
            continue

        # --------------------------------------------------
        # Programme chemical combination
        # --------------------------------------------------

        programme_chemicals = (
            get_programme_chemicals(
                row.get(
                    "Chemical",
                    ""
                )
            )
        )

        if not programme_chemicals:
            continue

        programme_chemical_set = set(
            programme_chemicals
        )

        # --------------------------------------------------
        # EXACT chemical combination
        # --------------------------------------------------

        if (
            programme_chemical_set
            != application_chemical_set
        ):
            continue

        # --------------------------------------------------
        # Planned date
        # --------------------------------------------------

        planned_date = pd.to_datetime(
            row.get(
                "Planned Date"
            ),
            errors="coerce"
        )

        if pd.isna(
            planned_date
        ):
            continue

        planned_date = (
            planned_date.normalize()
        )

        actual_date_normalized = (
            pd.Timestamp(
                application_date
            ).normalize()
        )

        # --------------------------------------------------
        # Calculate date difference
        # --------------------------------------------------

        date_difference = (
            actual_date_normalized
            -
            planned_date
        ).days

        # Prefer planned date <= actual date.
        #
        # Example:
        #
        # Planned 10 Oct
        # Actual 12 Oct
        #
        # This is preferable to a programme row planned
        # for 20 Oct.
        #
        if date_difference >= 0:

            priority = 0
            distance = date_difference

        else:

            priority = 1
            distance = abs(
                date_difference
            )

        candidates.append(
            (
                priority,
                distance,
                index
            )
        )

    if not candidates:
        return None

    # ------------------------------------------------------
    # Best match
    # ------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        )
    )

    return candidates[0][2]

# ==========================================================
# SYNCHRONIZE HERBICIDE APPLICATIONS TO PROGRAMME
# ==========================================================

def sync_herbicide_applications_to_programme():
    """
    Reconcile ALL actual herbicide applications against the
    herbicide programme.

    IMPORTANT:

    This function reads:

        data/herbicide_records.xlsx

    and updates:

        data/herbicide_schedule.xlsx

    It does NOT delete or modify the actual application
    records.

    Existing historical applications are therefore included
    automatically.

    Programme rows are updated with:

        Actual Date
        Actual Quantity
        Status = APPLIED
    """

    # ------------------------------------------------------
    # Check actual application file
    # ------------------------------------------------------

    if not os.path.exists(
        HERBICIDE_FILE
    ):
        return 0

    # ------------------------------------------------------
    # Load actual applications
    # ------------------------------------------------------

    try:

        applications_df = pd.read_excel(
            HERBICIDE_FILE
        )

    except Exception as e:

        print(
            "Error loading herbicide "
            f"application records: {e}"
        )

        return 0

    if applications_df.empty:
        return 0

    # ------------------------------------------------------
    # Load programme
    # ------------------------------------------------------

    programme_df = load_herbicide_schedule()

    if programme_df.empty:
        return 0

    changed = False
    matched_count = 0

    # ------------------------------------------------------
    # Process every actual application
    # ------------------------------------------------------

    for _, application in (
        applications_df.iterrows()
    ):

        # --------------------------------------------------
        # Application date
        # --------------------------------------------------

        application_date = pd.to_datetime(
            application.get(
                "Date"
            ),
            errors="coerce"
        )

        if pd.isna(
            application_date
        ):
            continue

        application_date = (
            application_date.normalize()
        )

        # --------------------------------------------------
        # Season
        # --------------------------------------------------

        season = str(
            application.get(
                "Season",
                ""
            )
        ).strip()

        if not season:
            continue

        # --------------------------------------------------
        # Field
        # --------------------------------------------------

        field = str(
            application.get(
                "Field",
                ""
            )
        ).strip()

        if not field:
            continue

        # --------------------------------------------------
        # Get actual chemicals
        # --------------------------------------------------

        application_chemicals = (
            get_application_chemicals(
                application
            )
        )

        if not application_chemicals:
            continue

        # --------------------------------------------------
        # Find programme row
        # --------------------------------------------------

        match_index = (
            find_best_herbicide_programme_match(
                programme_df,
                season,
                field,
                application_date,
                application_chemicals
            )
        )

        if match_index is None:
            continue

        # --------------------------------------------------
        # Programme chemicals
        # --------------------------------------------------

        programme_chemicals = (
            get_programme_chemicals(
                programme_df.at[
                    match_index,
                    "Chemical"
                ]
            )
        )

        # --------------------------------------------------
        # Actual quantity
        # --------------------------------------------------

        actual_quantity = (
            build_actual_quantity(
                programme_chemicals,
                application_chemicals
            )
        )

        # --------------------------------------------------
        # Update programme
        # --------------------------------------------------

        programme_df.at[
            match_index,
            "Actual Date"
        ] = application_date

        programme_df.at[
            match_index,
            "Actual Quantity"
        ] = actual_quantity

        programme_df.at[
            match_index,
            "Status"
        ] = "APPLIED"

        matched_count += 1
        changed = True

    # ------------------------------------------------------
    # Save only if something changed
    # ------------------------------------------------------

    if changed:

        save_herbicide_schedule(
            programme_df
        )

    print(
        "Herbicide programme reconciliation: "
        f"{matched_count} application(s) synchronized."
    )

    return matched_count

# ==========================================================
# LOAD HERBICIDE SCHEDULE
# ==========================================================

def load_herbicide_schedule():
    """
    Load the herbicide programme.

    IMPORTANT:

    Cocktail Rate and Planned Quantity may contain text
    because a cocktail can contain several chemicals.

    Example:

        Rate:
            2 + 2.5 + 0.09

        Planned Quantity:
            6 + 7.5 + 0.27
    """

    if not os.path.exists(
            HERBICIDE_SCHEDULE_FILE
    ):
        return pd.DataFrame(
            columns=HERBICIDE_SCHEDULE_COLUMNS
        )

    try:

        df = pd.read_excel(
            HERBICIDE_SCHEDULE_FILE
        )

    except Exception as e:

        print(
            f"Error loading herbicide schedule: {e}"
        )

        return pd.DataFrame(
            columns=HERBICIDE_SCHEDULE_COLUMNS
        )

    # ------------------------------------------------------
    # ENSURE COLUMNS
    # ------------------------------------------------------

    for column in HERBICIDE_SCHEDULE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df = df[
        HERBICIDE_SCHEDULE_COLUMNS
    ].copy()

    # ------------------------------------------------------
    # TEXT COLUMNS
    # ------------------------------------------------------

    text_columns = [

        "Programme ID",

        "Season",

        "Field",

        "Crop Type",

        "Crop Situation",

        "Application Stage",

        "Chemical",

        "Rate",

        "Rate Unit",

        "Quantity Unit",

        "Trigger",

        "Status",

        "Notes"

    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ------------------------------------------------------
    # DATES
    # ------------------------------------------------------

    for column in [

        "Planned Date",

        "Trigger Date",

        "Actual Date"

    ]:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    # ------------------------------------------------------
    # NUMERIC COLUMNS
    # ------------------------------------------------------

    # Area remains numeric.

    df["Area (ha)"] = pd.to_numeric(
        df["Area (ha)"],
        errors="coerce"
    ).fillna(0)

    # Actual Quantity may be numeric for single chemicals
    # or text for cocktails.

    df["Actual Quantity"] = (
        df["Actual Quantity"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Planned Quantity can also be a cocktail string.

    df["Planned Quantity"] = (
        df["Planned Quantity"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    df["Status"] = (
        df["Status"]
        .replace(
            "",
            "SCHEDULED"
        )
        .fillna("SCHEDULED")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return df


# ==========================================================
# SAVE HERBICIDE SCHEDULE
# ==========================================================

def save_herbicide_schedule(df):
    os.makedirs(
        os.path.dirname(
            HERBICIDE_SCHEDULE_FILE
        ),
        exist_ok=True
    )

    for column in HERBICIDE_SCHEDULE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df = df[
        HERBICIDE_SCHEDULE_COLUMNS
    ].copy()

    df.to_excel(
        HERBICIDE_SCHEDULE_FILE,
        index=False
    )


# ==========================================================
# GENERATE HERBICIDE PROGRAMME ID
# ==========================================================

def generate_herbicide_programme_id(df):
    if (
            df is None
            or df.empty
            or "Programme ID" not in df.columns
    ):
        return "HP001"

    numbers = []

    for value in df[
        "Programme ID"
    ].astype(str):

        value = value.strip().upper()

        if value.startswith("HP"):

            try:

                numbers.append(
                    int(
                        value[2:]
                    )
                )

            except ValueError:

                pass

    if not numbers:
        return "HP001"

    return (
        f"HP{max(numbers) + 1:03d}"
    )


# ==========================================================
# HERBICIDE AREA
# ==========================================================

def herbicide_area_for_programme(value):
    """
    Apply the same practical area handling used by the
    agricultural programme.

    3.01–3.50 ha -> 3.000 ha

    Otherwise retain three decimal places.
    """

    try:

        area = float(
            value or 0
        )

    except (
            TypeError,
            ValueError
    ):

        return 0

    if 3.01 <= area <= 3.50:
        return 3.000

    return round(
        area,
        3
    )


# ==========================================================
# SINGLE RATE QUANTITY
# ==========================================================

def calculate_herbicide_quantity(
        area,
        rate
):
    """
    Calculate:

        Area × Rate

    Used for a SINGLE chemical rate.
    """

    try:

        area = float(
            area or 0
        )

        rate = float(
            rate or 0
        )

    except (
            TypeError,
            ValueError
    ):

        return None

    return round(
        area * rate,
        3
    )


# ==========================================================
# COCKTAIL QUANTITY
# ==========================================================

def calculate_herbicide_cocktail_quantities(
        area,
        rate_text
):
    """
    Calculate individual planned quantities for a cocktail.

    Example:

        Area:
            3

        Rate:
            2 + 2.5 + 0.09

    Returns:

        6 + 7.5 + 0.27
    """

    try:

        area = float(
            area or 0
        )

    except (
            TypeError,
            ValueError
    ):

        return ""

    rate_parts = [

        part.strip()

        for part in str(
            rate_text or ""
        ).split("+")

        if part.strip()

    ]

    if not rate_parts:
        return ""

    quantities = []

    for rate_part in rate_parts:

        try:

            rate = float(
                rate_part
            )

            quantity = round(
                area * rate,
                3
            )

            quantities.append(
                str(quantity)
            )

        except (
                TypeError,
                ValueError
        ):

            quantities.append("")

    return " + ".join(
        quantities
    )


# ==========================================================
# HERBICIDE PLANNED QUANTITY
# ==========================================================

def calculate_herbicide_planned_quantity(
        area,
        rate
):
    """
    Calculate planned quantity for either:

        Single chemical
        OR
        Cocktail
    """

    rate_text = str(
        rate or ""
    ).strip()

    if not rate_text:
        return ""

    if "+" in rate_text:
        return calculate_herbicide_cocktail_quantities(
            area,
            rate_text
        )

    quantity = calculate_herbicide_quantity(
        area,
        rate_text
    )

    if quantity is None:
        return ""

    return str(
        quantity
    )


# ==========================================================
# FIELD SITUATION
# ==========================================================

def get_herbicide_field_situation(field):
    """
    DCGL field convention:

        DG = Main Estate / Irrigated

        L  = Liwaladzi / Rain-fed

        M  = Kasitu / Rain-fed
    """

    field = str(
        field or ""
    ).strip().upper()

    if field.startswith("DG"):
        return "Irrigated"

    if field.startswith("L"):
        return "Rain-fed"

    if field.startswith("M"):
        return "Rain-fed"

    return "All"


# ==========================================================
# HERBICIDE STAGE ORDER
# ==========================================================

def herbicide_stage_order(stage):
    order = {

        "PRE-EMERGENT":
            1,

        "EARLY-POST EMERGENT":
            2,

        "POST-EMERGENT":
            3

    }

    return order.get(
        str(stage or "")
        .strip()
        .upper(),
        99
    )


# ==========================================================
# UPDATE HERBICIDE PROGRAMME STATUS
# ==========================================================

def update_herbicide_programme_status(df):
    """
    Determine programme status.

    Actual Date = APPLIED.

    Otherwise:

        Past planned date     -> OVERDUE

        Today                 -> DUE TODAY

        Within 7 days         -> DUE SOON

        Future                -> SCHEDULED

    """

    if df.empty:
        return df

    today = (
        pd.Timestamp.today()
        .normalize()
    )

    for index, row in df.iterrows():

        actual_date = pd.to_datetime(
            row.get(
                "Actual Date"
            ),
            errors="coerce"
        )

        if pd.notna(
                actual_date
        ):
            df.at[
                index,
                "Status"
            ] = "APPLIED"

            continue

        planned_date = pd.to_datetime(
            row.get(
                "Planned Date"
            ),
            errors="coerce"
        )

        if pd.isna(
                planned_date
        ):
            df.at[
                index,
                "Status"
            ] = "NO DATE"

            continue

        planned_date = (
            planned_date.normalize()
        )

        if planned_date < today:

            df.at[
                index,
                "Status"
            ] = "OVERDUE"


        elif planned_date == today:

            df.at[
                index,
                "Status"
            ] = "DUE TODAY"


        elif planned_date <= (
                today
                +
                pd.Timedelta(
                    days=7
                )
        ):

            df.at[
                index,
                "Status"
            ] = "DUE SOON"


        else:

            df.at[
                index,
                "Status"
            ] = "SCHEDULED"

    return df


# ==========================================================
# GENERATE HERBICIDE PROGRAMME
# ==========================================================

@activity_bp.route(
    "/agriculture/generate-herbicide-programme",
    methods=["POST"]
)
def generate_herbicide_programme():

    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import get_active_season

    season = get_active_season()

    season_text = str(
        season or ""
    ).strip()

    season_normalised = (
        season_text
        .replace(
            " ",
            ""
        )
    )

    # ======================================================
    # ROLE
    # ======================================================

    allowed_roles = [

        "Admin",

        "Manager",

        "Agriculture Manager"

    ]

    if session.get("role") not in allowed_roles:

        flash(
            "You do not have permission to generate "
            "the herbicide programme.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # LOAD RULES
    # ======================================================

    rules = load_herbicide_rules()

    if rules.empty:

        flash(
            f"No herbicide rules exist for season "
            f"{season_text}. Create or copy the rules first.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_rules"
            )
        )

    # ======================================================
    # NORMALISE RULE SEASON
    # ======================================================

    rules["_SeasonNormalised"] = (
        rules["Season"]
        .astype(str)
        .str.strip()
        .str.replace(
            " ",
            "",
            regex=False
        )
    )

    rules = rules[
        rules["_SeasonNormalised"]
        ==
        season_normalised
    ].copy()

    rules.drop(
        columns=[
            "_SeasonNormalised"
        ],
        inplace=True
    )

    # ======================================================
    # ACTIVE RULES
    # ======================================================

    rules = rules[
        rules["Active"]
        .astype(str)
        .str.strip()
        .str.upper()
        ==
        "YES"
    ].copy()

    if rules.empty:

        flash(
            f"No active herbicide rules exist for "
            f"season {season_text}.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_rules"
            )
        )

    # ======================================================
    # LOAD CATALOGUE
    # ======================================================

    catalogue_df = (
        load_herbicide_catalogue()
    )

    if catalogue_df.empty:

        flash(
            "The herbicide chemical catalogue is empty. "
            "Add active chemicals and rates before "
            "generating the programme.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_catalogue"
            )
        )

    # ======================================================
    # NORMALISE CATALOGUE SEASON
    # ======================================================

    catalogue_df["_SeasonNormalised"] = (
        catalogue_df["Season"]
        .astype(str)
        .str.strip()
        .str.replace(
            " ",
            "",
            regex=False
        )
    )

    # ======================================================
    # ACTIVE CURRENT-SEASON CATALOGUE
    # ======================================================

    active_catalogue = catalogue_df[
        (
            catalogue_df["_SeasonNormalised"]
            ==
            season_normalised
        )
        &
        (
            catalogue_df["Active"]
            .astype(str)
            .str.strip()
            .str.upper()
            ==
            "YES"
        )
    ].copy()

    if active_catalogue.empty:

        flash(
            f"No active chemicals exist in the "
            f"{season_text} herbicide catalogue.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_catalogue"
            )
        )

    # ======================================================
    # LOAD REGISTERED FIELDS
    # ======================================================

    field_file = (
        "data/registered_fields.xlsx"
    )

    if not os.path.exists(
        field_file
    ):

        flash(
            "Registered fields file was not found.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    try:

        fields_df = pd.read_excel(
            field_file,
            engine="openpyxl"
        )

    except Exception as e:

        flash(
            f"Unable to read registered fields: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    fields_df.columns = (
        fields_df.columns
        .astype(str)
        .str.strip()
    )

    # ======================================================
    # REQUIRED FIELD COLUMNS
    # ======================================================

    required_columns = [

        "Field",

        "Hectares"

    ]

    missing_columns = [

        column

        for column in required_columns

        if column not in fields_df.columns

    ]

    if missing_columns:

        flash(
            "Registered fields file is missing: "
            +
            ", ".join(
                missing_columns
            ),
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # FIELD SEASON FILTER
    # ======================================================

    if "Season" in fields_df.columns:

        fields_df["_SeasonNormalised"] = (
            fields_df["Season"]
            .astype(str)
            .str.strip()
            .str.replace(
                " ",
                "",
                regex=False
            )
        )

        fields_df = fields_df[
            fields_df["_SeasonNormalised"]
            ==
            season_normalised
        ].copy()

        fields_df.drop(
            columns=[
                "_SeasonNormalised"
            ],
            inplace=True
        )

    # ======================================================
    # CHECK FIELDS
    # ======================================================

    if fields_df.empty:

        flash(
            f"No registered fields were found for "
            f"season {season_text}. Check the Season "
            f"column in registered_fields.xlsx.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # LOAD EXISTING PROGRAMME
    # ======================================================

    existing = (
        load_herbicide_schedule()
    )

    if existing.empty:

        existing_season = pd.DataFrame(
            columns=HERBICIDE_SCHEDULE_COLUMNS
        )

    else:

        existing_season = existing[
            existing["Season"]
            .astype(str)
            .str.strip()
            .str.replace(
                " ",
                "",
                regex=False
            )
            ==
            season_normalised
        ].copy()

    # ======================================================
    # NEXT PROGRAMME ID
    # ======================================================

    next_id = (
        generate_herbicide_programme_id(
            existing
        )
    )

    generated = []

    # ======================================================
    # DIAGNOSTIC COUNTERS
    # ======================================================

    diagnostic = {

        "fields":
            len(fields_df),

        "field_rules":
            0,

        "trigger_found":
            0,

        "trigger_missing":
            0,

        "dates_created":
            0,

        "dates_missing":
            0,

        "quantities_created":
            0,

        "catalogue_missing":
            0

    }

    # ======================================================
    # LOAD ACTIVITY EVENTS ONCE
    # ======================================================

    activity_events = (
        load_herbicide_activity_events(
            season
        )
    )

    # ======================================================
    # FIELD LOOP
    # ======================================================

    for _, field_row in fields_df.iterrows():

        field = str(
            field_row.get(
                "Field",
                ""
            )
        ).strip()

        if not field:
            continue

        area = (
            herbicide_area_for_programme(
                field_row.get(
                    "Hectares",
                    0
                )
            )
        )

        if area <= 0:
            continue

        # ==================================================
        # FIELD SITUATION
        # ==================================================

        situation = (
            get_herbicide_field_situation(
                field
            )
        )

        # ==================================================
        # MATCH RULES
        # ==================================================

        field_rules = rules[
            (
                rules[
                    "Crop Situation"
                ]
                .astype(str)
                .str.strip()
                .str.lower()
                ==
                situation.lower()
            )
            |
            (
                rules[
                    "Crop Situation"
                ]
                .astype(str)
                .str.strip()
                .str.lower()
                ==
                "all"
            )
        ].copy()

        if field_rules.empty:
            continue

        diagnostic[
            "field_rules"
        ] += len(field_rules)

        # ==================================================
        # RULE LOOP
        # ==================================================

        for _, rule in field_rules.iterrows():

            stage = str(
                rule.get(
                    "Application Stage",
                    ""
                )
            ).strip()

            chemical_text = str(
                rule.get(
                    "Chemical",
                    ""
                )
            ).strip()

            trigger = str(
                rule.get(
                    "Trigger",
                    ""
                )
            ).strip()

            timing_type = str(
                rule.get(
                    "Timing Type",
                    ""
                )
            ).strip()

            timing_value = rule.get(
                "Timing Value",
                ""
            )

            if not chemical_text:
                continue

            # =================================================
            # CHEMICALS FROM RULE
            # =================================================

            chemical_names = [

                item.strip()

                for item in chemical_text.split(
                    "+"
                )

                if item.strip()

            ]

            if not chemical_names:
                continue

            # =================================================
            # VALIDATE AGAINST CATALOGUE
            # =================================================

            catalogue_entries = (
                get_rule_chemicals_from_catalogue(
                    chemical_names,
                    season_text,
                    active_catalogue
                )
            )

            if catalogue_entries is None:

                diagnostic[
                    "catalogue_missing"
                ] += 1

                print(
                    "[HERBICIDE GENERATOR] "
                    f"Catalogue validation failed for "
                    f"{field}: {chemical_text}"
                )

                continue

            # =================================================
            # BUILD RATE FROM CURRENT CATALOGUE
            # =================================================

            rate, rate_unit = (
                build_herbicide_rule_rate(
                    catalogue_entries
                )
            )

            if not rate:
                continue

            # =================================================
            # TRIGGER DATE
            # =================================================

            trigger_date = None

            if trigger in [

                "Planting",

                "Harvesting",

                "Seedcane Cutting"

            ]:

                trigger_date = (
                    get_herbicide_trigger_date(
                        field=field,
                        trigger=trigger,
                        season=season_text,
                        events_df=activity_events
                    )
                )

                if trigger_date is not None:

                    diagnostic[
                        "trigger_found"
                    ] += 1

                else:

                    diagnostic[
                        "trigger_missing"
                    ] += 1

            # =================================================
            # PLANNED DATE
            # =================================================

            planned_date = (
                calculate_herbicide_planned_date(
                    trigger_date=trigger_date,
                    timing_type=timing_type,
                    timing_value=timing_value,
                    season=season_text,
                    field_situation=situation
                )
            )

            if planned_date is None:

                diagnostic[
                    "dates_missing"
                ] += 1

                continue

            planned_date = pd.to_datetime(
                planned_date,
                errors="coerce"
            )

            if pd.isna(
                planned_date
            ):

                diagnostic[
                    "dates_missing"
                ] += 1

                continue

            diagnostic[
                "dates_created"
            ] += 1

            # =================================================
            # PLANNED QUANTITY
            # =================================================

            planned_quantity = (
                calculate_herbicide_planned_quantity(
                    area,
                    rate
                )
            )

            if not planned_quantity:
                continue

            diagnostic[
                "quantities_created"
            ] += 1

            # =================================================
            # CROP TYPE
            # =================================================

            crop_type = str(
                field_row.get(
                    "Crop Name",
                    ""
                )
            ).strip()

            # =================================================
            # PROGRAMME ENTRY
            # =================================================

            generated.append({

                "Programme ID":
                    next_id,

                "Season":
                    season_text,

                "Field":
                    field,

                "Crop Type":
                    crop_type,

                "Crop Situation":
                    situation,

                "Application Stage":
                    stage,

                "Chemical":
                    chemical_text,

                "Planned Date":
                    planned_date,

                "Rate":
                    rate,

                "Rate Unit":
                    rate_unit,

                "Area (ha)":
                    area,

                "Planned Quantity":
                    planned_quantity,

                "Quantity Unit":
                    rate_unit,

                "Trigger":
                    trigger,

                "Trigger Date":
                    trigger_date,

                "Status":
                    "SCHEDULED",

                "Actual Date":
                    "",

                "Actual Quantity":
                    "",

                "Notes":
                    ""

            })

            # =================================================
            # NEXT ID
            # =================================================

            try:

                number = (
                    int(
                        next_id[2:]
                    )
                    + 1
                )

            except Exception:

                number = 1

            next_id = (
                f"HP{number:03d}"
            )

    # ======================================================
    # NOTHING GENERATED
    # ======================================================

    if not generated:

        print(
            "=================================================="
        )

        print(
            "[HERBICIDE GENERATOR] "
            "NO PROGRAMME GENERATED"
        )

        print(
            f"Season: {season_text}"
        )

        print(
            f"Fields: {diagnostic['fields']}"
        )

        print(
            f"Field-rule matches: "
            f"{diagnostic['field_rules']}"
        )

        print(
            f"Triggers found: "
            f"{diagnostic['trigger_found']}"
        )

        print(
            f"Triggers missing: "
            f"{diagnostic['trigger_missing']}"
        )

        print(
            f"Dates created: "
            f"{diagnostic['dates_created']}"
        )

        print(
            f"Dates missing: "
            f"{diagnostic['dates_missing']}"
        )

        print(
            f"Catalogue failures: "
            f"{diagnostic['catalogue_missing']}"
        )

        print(
            "=================================================="
        )

        # --------------------------------------------------
        # USER-FACING DIAGNOSTIC
        # --------------------------------------------------

        if diagnostic["fields"] == 0:

            message = (
                f"No registered fields were found for "
                f"{season_text}."
            )

        elif diagnostic["field_rules"] == 0:

            message = (
                f"No active herbicide rules match the "
                f"registered field situations for {season_text}."
            )

        elif (
            diagnostic["dates_missing"] > 0
            and
            diagnostic["dates_created"] == 0
        ):

            message = (
                "Herbicide rules were found, but no planned "
                "application dates could be calculated. "
                "Check the rule Trigger, Timing Type, "
                "Timing Value and activity records."
            )

        elif diagnostic["catalogue_missing"] > 0:

            message = (
                "Some herbicide rules reference chemicals "
                "that are not active in the current-season "
                "chemical catalogue."
            )

        else:

            message = (
                "No herbicide programme entries could be "
                "generated. Check the Flask console for the "
                "generation diagnostics."
            )

        flash(
            message,
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # GENERATED DATAFRAME
    # ======================================================

    generated_df = pd.DataFrame(
        generated,
        columns=HERBICIDE_SCHEDULE_COLUMNS
    )

    # ======================================================
    # DUPLICATE PREVENTION
    # ======================================================

    if not existing.empty:

        existing_keys = set()

        for _, row in existing.iterrows():

            planned = pd.to_datetime(
                row.get(
                    "Planned Date"
                ),
                errors="coerce"
            )

            planned_key = (
                planned.strftime(
                    "%Y-%m-%d"
                )
                if pd.notna(planned)
                else
                str(
                    row.get(
                        "Planned Date",
                        ""
                    )
                ).strip()
            )

            existing_keys.add(
                (

                    str(
                        row.get(
                            "Season",
                            ""
                        )
                    )
                    .strip()
                    .replace(
                        " ",
                        ""
                    ),

                    str(
                        row.get(
                            "Field",
                            ""
                        )
                    ).strip(),

                    str(
                        row.get(
                            "Application Stage",
                            ""
                        )
                    ).strip(),

                    str(
                        row.get(
                            "Chemical",
                            ""
                        )
                    ).strip(),

                    planned_key

                )
            )

        # --------------------------------------------------
        # GENERATED KEYS
        # --------------------------------------------------

        def generated_key(row):

            planned = pd.to_datetime(
                row["Planned Date"],
                errors="coerce"
            )

            planned_key = (
                planned.strftime(
                    "%Y-%m-%d"
                )
                if pd.notna(planned)
                else
                str(
                    row["Planned Date"]
                ).strip()
            )

            return (

                str(
                    row["Season"]
                )
                .strip()
                .replace(
                    " ",
                    ""
                ),

                str(
                    row["Field"]
                ).strip(),

                str(
                    row[
                        "Application Stage"
                    ]
                ).strip(),

                str(
                    row["Chemical"]
                ).strip(),

                planned_key

            )

        generated_df = generated_df[
            ~generated_df.apply(
                lambda row:
                generated_key(row)
                in existing_keys,
                axis=1
            )
        ].copy()

    # ======================================================
    # ALL ALREADY EXIST
    # ======================================================

    if generated_df.empty:

        flash(
            "The herbicide programme already contains "
            "these entries.",
            "info"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # COMBINE
    # ======================================================

    final_df = pd.concat(
        [
            existing,
            generated_df
        ],
        ignore_index=True
    )

    # ======================================================
    # SAVE
    # ======================================================

    save_herbicide_schedule(
        final_df
    )

    # ======================================================
    # SUCCESS
    # ======================================================

    flash(
        f"{len(generated_df)} herbicide programme "
        f"entry(s) generated for season {season_text}.",
        "success"
    )

    return redirect(
        url_for(
            "activities.herbicide_programme"
        )
    )


# ==========================================================
# HERBICIDE PROGRAMME PAGE
# ==========================================================

@activity_bp.route(
    "/agriculture/herbicide-programme"
)
def herbicide_programme():

    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    # ======================================================
    # SYNCHRONIZE ACTUAL APPLICATIONS
    # ======================================================
    #
    # IMPORTANT:
    #
    # This reconciles ALL existing herbicide applications
    # from:
    #
    #     data/herbicide_records.xlsx
    #
    # against:
    #
    #     data/herbicide_schedule.xlsx
    #
    # Therefore applications that were recorded BEFORE this
    # synchronization feature was introduced will also be
    # recognized.
    #
    # The actual application records are NOT deleted or
    # modified.
    #
    # Matching is based on:
    #
    #     Season
    #     Field
    #     Exact chemical combination
    #     Planned/Actual date relationship
    #
    # Matching programme entries are updated with:
    #
    #     Actual Date
    #     Actual Quantity
    #     Status = APPLIED
    #

    try:

        sync_herbicide_applications_to_programme()

    except Exception as e:

        print(
            "Herbicide programme synchronization error:"
        )

        print(e)

    # ======================================================
    # LOAD HERBICIDE PROGRAMME
    # ======================================================

    df = load_herbicide_schedule()

    # ======================================================
    # FILTER ACTIVE SEASON
    # ======================================================

    if not df.empty:
        df = df[
            df["Season"]
            .astype(str)
            .str.strip()
            ==
            str(season).strip()
            ].copy()

        # ==================================================
        # UPDATE PROGRAMME STATUS
        # ==================================================

        df = (
            update_herbicide_programme_status(
                df
            )
        )

    # ======================================================
    # CHECK WHETHER ACTIVE-SEASON PROGRAMME EXISTS
    # ======================================================

    programme_generated = not df.empty

    # ======================================================
    # STAGE ORDER
    # ======================================================

    if not df.empty:
        df["_StageOrder"] = (
            df[
                "Application Stage"
            ]
            .astype(str)
            .str.upper()
            .map(
                {
                    "PRE-EMERGENT":
                        1,

                    "EARLY-POST EMERGENT":
                        2,

                    "POST-EMERGENT":
                        3
                }
            )
            .fillna(99)
        )

        # ==================================================
        # SORT PROGRAMME
        # ==================================================

        df = df.sort_values(
            [
                "Planned Date",
                "Field",
                "_StageOrder"
            ]
        )

        # ==================================================
        # REMOVE INTERNAL SORT COLUMN
        # ==================================================

        df = df.drop(
            columns=[
                "_StageOrder"
            ]
        )

    # ======================================================
    # RECORDS
    # ======================================================

    records = (

        df.to_dict(
            orient="records"
        )

        if not df.empty

        else []

    )

    # ======================================================
    # SUMMARY
    # ======================================================

    summary = {

        "total":
            len(df),

        "scheduled":
            0,

        "overdue":
            0,

        "due_today":
            0,

        "due_soon":
            0,

        "applied":
            0

    }

    # ======================================================
    # CALCULATE SUMMARY COUNTS
    # ======================================================

    if not df.empty:

        statuses = (
            df["Status"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        # --------------------------------------------------
        # SCHEDULED
        # --------------------------------------------------

        summary["scheduled"] = int(
            (
                statuses
                ==
                "SCHEDULED"
            ).sum()
        )

        # --------------------------------------------------
        # OVERDUE
        # --------------------------------------------------

        summary["overdue"] = int(
            (
                statuses
                ==
                "OVERDUE"
            ).sum()
        )

        # --------------------------------------------------
        # DUE TODAY
        # --------------------------------------------------

        summary["due_today"] = int(
            (
                statuses
                ==
                "DUE TODAY"
            ).sum()
        )

        # --------------------------------------------------
        # DUE SOON
        # --------------------------------------------------

        summary["due_soon"] = int(
            (
                statuses
                ==
                "DUE SOON"
            ).sum()
        )

        # --------------------------------------------------
        # APPLIED
        # --------------------------------------------------

        summary["applied"] = int(
            (
                statuses
                ==
                "APPLIED"
            ).sum()
        )

    # ======================================================
    # CHECK PROGRAMME REQUEST STATUS
    # ======================================================
    #
    # Determine which programme lines already have an
    # Agriculture Request in chemical_requests.xlsx.
    #
    # Matching is based on:
    #
    #     Season
    #     Programme ID
    #
    # This prevents the same programme line from being
    # requested more than once.
    #

    requests_df = load_chemical_requests()

    requested_programmes = set()

    if not requests_df.empty:

        # --------------------------------------------------
        # ACTIVE SEASON
        # --------------------------------------------------

        requests_df = requests_df[
            requests_df["Season"]
            .astype(str)
            .str.strip()
            ==
            str(season).strip()
        ].copy()

        # --------------------------------------------------
        # ACTIVE REQUEST STATUSES
        # --------------------------------------------------
        #
        # A programme is considered already processed if
        # there is an active request in any of these states.
        #

        active_request_statuses = [
            "PENDING",
            "APPROVED",
            "PARTIAL",
            "ISSUED"
        ]

        requests_df = requests_df[
            requests_df["Status"]
            .astype(str)
            .str.upper()
            .str.strip()
            .isin(
                active_request_statuses
            )
        ].copy()

        # --------------------------------------------------
        # PROGRAMME IDS
        # --------------------------------------------------

        if "Programme ID" in requests_df.columns:

            requested_programmes = set(
                requests_df["Programme ID"]
                .astype(str)
                .str.strip()
                .replace(
                    "",
                    pd.NA
                )
                .dropna()
                .tolist()
            )

    # ======================================================
    # ADD REQUEST STATUS TO EACH PROGRAMME ROW
    # ======================================================

    for row in records:

        programme_id = str(
            row.get(
                "Programme ID",
                ""
            )
        ).strip()

        row["Request Exists"] = (
            programme_id
            in
            requested_programmes
        )

    # ======================================================
    # RENDER PAGE
    # ======================================================

    return render_template(

        "agriculture/herbicide_programme.html",

        season=season,

        records=records,

        summary=summary,

        programme_generated=programme_generated
    )

# ==========================================================
# HERBICIDE CHEMICAL CATALOGUE PAGE
# ==========================================================

@activity_bp.route(
    "/agriculture/herbicide-catalogue",
    methods=["GET", "POST"]
)
def herbicide_catalogue():
    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    # ======================================================
    # ROLE CONTROL
    # ======================================================

    allowed_roles = [

        "Admin",

        "Manager",

        "Agriculture Manager"

    ]

    if session.get("role") not in allowed_roles:
        flash(
            "You do not have permission to manage "
            "the herbicide chemical catalogue.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_menu"
            )
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    # ======================================================
    # LOAD CATALOGUE
    # ======================================================

    df = load_herbicide_catalogue()

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        action = (
            request.form.get(
                "action",
                "add"
            )
            .strip()
            .lower()
        )

        # ==================================================
        # ADD CHEMICAL
        # ==================================================

        if action == "add":

            chemical = (
                request.form.get(
                    "Chemical",
                    ""
                )
                .strip()
            )

            rate = (
                request.form.get(
                    "Rate",
                    ""
                )
                .strip()
            )

            rate_unit = (
                request.form.get(
                    "Rate Unit",
                    "L/ha"
                )
                .strip()
            )

            notes = (
                request.form.get(
                    "Notes",
                    ""
                )
                .strip()
            )

            # ------------------------------------------------
            # VALIDATE NAME
            # ------------------------------------------------

            if not chemical:
                flash(
                    "Chemical name is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_catalogue"
                    )
                )

            # ------------------------------------------------
            # VALIDATE RATE
            # ------------------------------------------------

            try:

                numeric_rate = float(
                    rate
                )

            except (
                    TypeError,
                    ValueError
            ):

                flash(
                    "A valid numeric chemical rate is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_catalogue"
                    )
                )

            if numeric_rate <= 0:
                flash(
                    "Chemical rate must be greater than zero.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_catalogue"
                    )
                )

            # ------------------------------------------------
            # DUPLICATE CHECK
            # ------------------------------------------------

            duplicate = df[

                (
                        df["Season"]
                        .astype(str)
                        .str.strip()
                        ==
                        str(season).strip()
                )

                &

                (
                        df["Chemical"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        ==
                        chemical.lower()
                )

                ]

            if not duplicate.empty:
                flash(
                    f"{chemical} already exists in the "
                    f"{season} chemical catalogue.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "activities.herbicide_catalogue"
                    )
                )

            # ------------------------------------------------
            # ADD
            # ------------------------------------------------

            data = {

                "Season":
                    season,

                "Chemical":
                    chemical,

                "Rate":
                    numeric_rate,

                "Rate Unit":
                    rate_unit,

                "Active":
                    "YES",

                "Notes":
                    notes

            }

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [data]
                    )
                ],
                ignore_index=True
            )

            save_herbicide_catalogue(
                df
            )

            flash(
                f"{chemical} added to the {season} "
                "herbicide chemical catalogue.",
                "success"
            )

            return redirect(
                url_for(
                    "activities.herbicide_catalogue"
                )
            )


        # ==================================================
        # TOGGLE CHEMICAL
        # ==================================================

        elif action == "toggle":

            chemical = (
                request.form.get(
                    "Chemical",
                    ""
                )
                .strip()
            )

            matches = df[

                (
                        df["Season"]
                        .astype(str)
                        .str.strip()
                        ==
                        str(season).strip()
                )

                &

                (
                        df["Chemical"]
                        .astype(str)
                        .str.strip()
                        ==
                        chemical
                )

                ]

            if not matches.empty:

                index = matches.index[0]

                current = (
                    str(
                        df.at[
                            index,
                            "Active"
                        ]
                    )
                    .strip()
                    .upper()
                )

                df.at[
                    index,
                    "Active"
                ] = (

                    "NO"

                    if current == "YES"

                    else "YES"

                )

                save_herbicide_catalogue(
                    df
                )

                flash(
                    f"{chemical} catalogue status updated.",
                    "success"
                )


            else:

                flash(
                    f"Chemical '{chemical}' was not found.",
                    "warning"
                )

            return redirect(
                url_for(
                    "activities.herbicide_catalogue"
                )
            )

    # ======================================================
    # CURRENT SEASON
    # ======================================================

    current_catalogue = df[

        df["Season"]
        .astype(str)
        .str.strip()
        ==
        str(season).strip()

        ].copy()

    current_catalogue = (
        current_catalogue
        .sort_values(
            "Chemical"
        )
    )

    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "agriculture/herbicide_catalogue.html",

        season=season,

        chemical_catalog=current_catalogue.to_dict(
            orient="records"
        ),

        rate_units=[
            "L/ha",
            "kg/ha",
            "g/ha"
        ]

    )

# ==========================================================
# AGRICULTURE REQUEST REGISTER
# ==========================================================

CHEMICAL_REQUEST_FILE = "data/chemical_requests.xlsx"

CHEMICAL_REQUEST_COLUMNS = [
    "Request ID",
    "Request Date",
    "Season",

    # ------------------------------------------------------
    # REQUEST CLASSIFICATION
    # ------------------------------------------------------
    "Request Type",
    "Request Category",

    # ------------------------------------------------------
    # REQUESTER / DEPARTMENT
    # ------------------------------------------------------
    "Department",
    "Requester",

    # ------------------------------------------------------
    # FIELD / PROGRAMME INFORMATION
    # ------------------------------------------------------
    "Field",
    "Programme ID",
    "Crop Type",
    "Crop Situation",
    "Application Stage",

    # ------------------------------------------------------
    # ITEM INFORMATION
    # ------------------------------------------------------
    "Chemical",
    "Item / Description",
    "Specification",
    "Rate",
    "Rate Unit",
    "Area (ha)",

    # ------------------------------------------------------
    # QUANTITY
    # ------------------------------------------------------
    "Required Quantity",
    "Quantity Unit",
    "Requested Quantity",

    # ------------------------------------------------------
    # DATES / PRIORITY
    # ------------------------------------------------------
    "Planned Date",
    "Required Date",
    "Urgency",

    # ------------------------------------------------------
    # JUSTIFICATION
    # ------------------------------------------------------
    "Reason",
    "Notes",

    # ------------------------------------------------------
    # AGRICULTURE APPROVAL
    # ------------------------------------------------------
    "Status",
    "Approved By",
    "Approval Date",
    "Rejection Reason",

    # ------------------------------------------------------
    # STORES HAND-OFF
    # ------------------------------------------------------
    "Stores Request ID",
    "Stores Request Date",

    # ------------------------------------------------------
    # STORES ISSUE
    # ------------------------------------------------------
    "Issued Quantity",
    "Issue Date"
]

# ==========================================================
# LOAD AGRICULTURE REQUESTS
# ==========================================================

def load_chemical_requests():

    if not os.path.exists(CHEMICAL_REQUEST_FILE):
        return pd.DataFrame(columns=CHEMICAL_REQUEST_COLUMNS)

    try:
        df = pd.read_excel(CHEMICAL_REQUEST_FILE)

    except Exception as e:
        print("Error loading agriculture requests:", e)

        return pd.DataFrame(columns=CHEMICAL_REQUEST_COLUMNS)

    # ======================================================
    # ADD MISSING COLUMNS
    # ======================================================
    #
    # This is important for backward compatibility.
    #
    # Existing chemical_requests.xlsx files will not break.
    # Any newly introduced columns are simply added with
    # appropriate default values.
    #
    # ======================================================

    for column in CHEMICAL_REQUEST_COLUMNS:

        if column not in df.columns:

            if column == "Request Type":
                df[column] = "PROGRAMME"

            elif column == "Request Category":
                df[column] = "HERBICIDE"

            elif column == "Urgency":
                df[column] = "NORMAL"

            elif column == "Status":
                df[column] = "PENDING"

            else:
                df[column] = ""

    # ======================================================
    # KEEP ONLY STANDARD COLUMNS
    # ======================================================

    df = df[CHEMICAL_REQUEST_COLUMNS].copy()

    # ======================================================
    # TEXT COLUMNS
    # ======================================================

    text_columns = [
        "Request ID",
        "Season",
        "Request Type",
        "Request Category",
        "Department",
        "Requester",
        "Field",
        "Programme ID",
        "Crop Type",
        "Crop Situation",
        "Application Stage",
        "Chemical",
        "Item / Description",
        "Specification",
        "Rate",
        "Rate Unit",
        "Quantity Unit",
        "Urgency",
        "Reason",
        "Notes",
        "Status",
        "Approved By",
        "Rejection Reason",
        "Stores Request ID"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ======================================================
    # REQUEST TYPE
    # ======================================================

    df["Request Type"] = (
        df["Request Type"]
        .replace("", "PROGRAMME")
        .fillna("PROGRAMME")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # ======================================================
    # REQUEST CATEGORY
    # ======================================================

    #
    # Existing requests are chemical requests.
    # Therefore old records automatically become HERBICIDE
    # unless a category has already been assigned.
    #

    df["Request Category"] = (
        df["Request Category"]
        .replace("", "HERBICIDE")
        .fillna("HERBICIDE")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # ======================================================
    # URGENCY
    # ======================================================

    df["Urgency"] = (
        df["Urgency"]
        .replace("", "NORMAL")
        .fillna("NORMAL")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # ======================================================
    # STATUS
    # ======================================================

    df["Status"] = (
        df["Status"]
        .replace("", "PENDING")
        .fillna("PENDING")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # ======================================================
    # DATE COLUMNS
    # ======================================================

    date_columns = [
        "Request Date",
        "Planned Date",
        "Required Date",
        "Approval Date",
        "Stores Request Date",
        "Issue Date"
    ]

    for column in date_columns:

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    # ======================================================
    # AREA
    # ======================================================

    df["Area (ha)"] = pd.to_numeric(
        df["Area (ha)"],
        errors="coerce"
    ).fillna(0)

    # ======================================================
    # QUANTITY FIELDS
    # ======================================================
    #
    # Keep quantities as strings because:
    #
    # - chemicals may use L
    # - fertilizers may use bags
    # - stationery may use reams
    # - fuel may use litres
    # - PPE may use pieces
    #
    # This also allows values such as:
    #
    #     10
    #     10.5
    #     5 + 5
    #
    # where necessary.
    #
    # ======================================================

    quantity_columns = [
        "Required Quantity",
        "Requested Quantity",
        "Issued Quantity"
    ]

    for column in quantity_columns:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ======================================================
    # BACKWARD COMPATIBILITY FOR ITEM / DESCRIPTION
    # ======================================================

    #
    # Existing chemical requests already have the Chemical
    # column. For those requests, use Chemical as the item
    # description when Item / Description is empty.
    #

    empty_item = (
        df["Item / Description"]
        .astype(str)
        .str.strip()
        == ""
    )

    df.loc[empty_item, "Item / Description"] = (
        df.loc[empty_item, "Chemical"]
    )

    return df

# ==========================================================
# SAVE AGRICULTURE REQUESTS
# ==========================================================

def save_chemical_requests(df):

    os.makedirs(
        os.path.dirname(CHEMICAL_REQUEST_FILE),
        exist_ok=True
    )

    # ======================================================
    # ENSURE ALL REQUIRED COLUMNS EXIST
    # ======================================================

    for column in CHEMICAL_REQUEST_COLUMNS:

        if column not in df.columns:

            if column == "Request Type":
                df[column] = "PROGRAMME"

            elif column == "Request Category":
                df[column] = "HERBICIDE"

            elif column == "Urgency":
                df[column] = "NORMAL"

            elif column == "Status":
                df[column] = "PENDING"

            else:
                df[column] = ""

    # ======================================================
    # COLUMN ORDER
    # ======================================================

    df = df[CHEMICAL_REQUEST_COLUMNS].copy()

    # ======================================================
    # REQUEST TYPE
    # ======================================================

    df["Request Type"] = (
        df["Request Type"]
        .fillna("PROGRAMME")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df.loc[
        df["Request Type"] == "",
        "Request Type"
    ] = "PROGRAMME"

    # ======================================================
    # REQUEST CATEGORY
    # ======================================================

    df["Request Category"] = (
        df["Request Category"]
        .fillna("HERBICIDE")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df.loc[
        df["Request Category"] == "",
        "Request Category"
    ] = "HERBICIDE"

    # ======================================================
    # URGENCY
    # ======================================================

    df["Urgency"] = (
        df["Urgency"]
        .fillna("NORMAL")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df.loc[
        df["Urgency"] == "",
        "Urgency"
    ] = "NORMAL"

    # ======================================================
    # STATUS
    # ======================================================

    df["Status"] = (
        df["Status"]
        .fillna("PENDING")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df.loc[
        df["Status"] == "",
        "Status"
    ] = "PENDING"

    # ======================================================
    # SAVE
    # ======================================================

    df.to_excel(
        CHEMICAL_REQUEST_FILE,
        index=False
    )

# ==========================================================
# GENERATE CHEMICAL REQUEST ID
# ==========================================================

def generate_chemical_request_id(
    df,
    season
):
    """
    Generate IDs such as:

        CR-2026/27-0001
        CR-2026/27-0002
        CR-2026/27-0003
    """

    season_text = (
        str(season)
        .strip()
        .replace(
            "/",
            "-"
        )
    )

    prefix = (
        f"CR-{season_text}-"
    )

    if df.empty:

        return (
            f"{prefix}0001"
        )

    existing_ids = (
        df["Request ID"]
        .astype(str)
        .str.strip()
        .tolist()
    )

    highest_number = 0

    for request_id in existing_ids:

        if not request_id.startswith(
            prefix
        ):
            continue

        try:

            number = int(
                request_id[
                    len(prefix):
                ]
            )

            highest_number = max(
                highest_number,
                number
            )

        except (
            ValueError,
            TypeError
        ):

            continue

    return (
        f"{prefix}"
        f"{highest_number + 1:04d}"
    )

# ==========================================================
# CHECK EXISTING CHEMICAL REQUEST
# ==========================================================

def operational_chemical_request_exists(
    df,
    field,
    chemical,
    reason
):
    """
    Prevent accidental duplicate operational requests.

    A request is considered a duplicate when there is already
    an active operational request for the same:

        - Field
        - Chemical
        - Reason

    Existing requests with final/rejected statuses are not blocked.
    """

    if df.empty:
        return False

    field = str(field).strip().upper()
    chemical = str(chemical).strip().upper()
    reason = str(reason).strip().upper()

    if not field or not chemical:
        return False

    operational = df[
        df["Request Type"]
        .astype(str)
        .str.upper()
        .str.strip()
        == "OPERATIONAL"
    ].copy()

    if operational.empty:
        return False

    matching = operational[
        (
            operational["Field"]
            .astype(str)
            .str.strip()
            .str.upper()
            == field
        )
        &
        (
            operational["Chemical"]
            .astype(str)
            .str.strip()
            .str.upper()
            == chemical
        )
        &
        (
            operational["Reason"]
            .astype(str)
            .str.strip()
            .str.upper()
            == reason
        )
    ].copy()

    if matching.empty:
        return False

    blocked_statuses = [
        "PENDING",
        "APPROVED",
        "PARTIAL",
        "ISSUED"
    ]

    matching_status = (
        matching["Status"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return bool(
        matching_status.isin(
            blocked_statuses
        ).any()
    )

def chemical_request_exists(
    df,
    programme_id
):
    """
    Check whether an active request already exists for
    a programme entry.

    Rejected requests do not block a new request.
    """

    if df.empty:
        return False

    programme_id = str(
        programme_id
    ).strip()

    if not programme_id:
        return False

    matching = df[
        df["Programme ID"]
        .astype(str)
        .str.strip()
        ==
        programme_id
    ].copy()

    if matching.empty:
        return False

    blocked_statuses = [
        "PENDING",
        "APPROVED",
        "PARTIAL",
        "ISSUED"
    ]

    matching_status = (
        matching["Status"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return bool(
        matching_status.isin(
            blocked_statuses
        ).any()
    )

# ==========================================================
# CHEMICAL REQUESTS PAGE
# ==========================================================

@activity_bp.route(
    "/agriculture/chemical-requests"
)
def chemical_requests():

    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    # ======================================================
    # LOAD REQUESTS
    # ======================================================

    df = load_chemical_requests()

    # ======================================================
    # FILTER ACTIVE SEASON
    # ======================================================

    if not df.empty:

        df = df[
            df["Season"]
            .astype(str)
            .str.strip()
            ==
            str(season).strip()
        ].copy()

        # --------------------------------------------------
        # Sort newest first
        # --------------------------------------------------

        df = df.sort_values(
            by=[
                "Request Date",
                "Request ID"
            ],
            ascending=[
                False,
                False
            ]
        )

    # ======================================================
    # RECORDS
    # ======================================================

    records = (

        df.to_dict(
            orient="records"
        )

        if not df.empty

        else []

    )

    # ======================================================
    # SUMMARY
    # ======================================================

    summary = {

        "total":
            len(df),

        "pending":
            0,

        "approved":
            0,

        "partial":
            0,

        "issued":
            0,

        "rejected":
            0

    }

    if not df.empty:

        statuses = (
            df["Status"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        summary["pending"] = int(
            (
                statuses
                ==
                "PENDING"
            ).sum()
        )

        summary["approved"] = int(
            (
                statuses
                ==
                "APPROVED"
            ).sum()
        )

        summary["partial"] = int(
            (
                statuses
                ==
                "PARTIAL"
            ).sum()
        )

        summary["issued"] = int(
            (
                statuses
                ==
                "ISSUED"
            ).sum()
        )

        summary["rejected"] = int(
            (
                statuses
                ==
                "REJECTED"
            ).sum()
        )

    # ======================================================
    # RENDER
    # ======================================================

    return render_template(
        "agriculture/chemical_requests.html",
        season=season,
        records=records,
        summary=summary
    )

# ==========================================================
# CREATE CHEMICAL REQUEST FROM PROGRAMME
# ==========================================================

@activity_bp.route(
    "/agriculture/chemical-request/<programme_id>",
    methods=[
        "GET",
        "POST"
    ]
)
def create_chemical_request(
    programme_id
):

    # ======================================================
    # LOGIN
    # ======================================================

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    # ======================================================
    # ACTIVE SEASON
    # ======================================================

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    # ======================================================
    # LOAD PROGRAMME
    # ======================================================

    programme_df = (
        load_herbicide_schedule()
    )

    if programme_df.empty:

        flash(
            "Herbicide programme is empty.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # FIND PROGRAMME ENTRY
    # ======================================================

    matching = programme_df[
        programme_df["Programme ID"]
        .astype(str)
        .str.strip()
        ==
        str(programme_id).strip()
    ].copy()

    # ======================================================
    # PROGRAMME NOT FOUND
    # ======================================================

    if matching.empty:

        flash(
            "Herbicide programme entry was not found.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    programme = (
        matching.iloc[0]
    )

    # ======================================================
    # CHECK SEASON
    # ======================================================

    programme_season = str(
        programme.get(
            "Season",
            ""
        )
    ).strip()

    if programme_season != str(
        season
    ).strip():

        flash(
            "This programme entry does not belong "
            "to the active season.",
            "danger"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # DO NOT REQUEST ALREADY APPLIED CHEMICAL
    # ======================================================

    actual_date = pd.to_datetime(
        programme.get(
            "Actual Date"
        ),
        errors="coerce"
    )

    if pd.notna(
        actual_date
    ):

        flash(
            "This herbicide programme entry has "
            "already been applied.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.herbicide_programme"
            )
        )

    # ======================================================
    # LOAD EXISTING REQUESTS
    # ======================================================

    requests_df = (
        load_chemical_requests()
    )

    # ======================================================
    # CHECK DUPLICATE REQUEST
    # ======================================================

    if chemical_request_exists(
        requests_df,
        programme_id
    ):

        flash(
            "A chemical request already exists "
            "for this programme entry.",
            "warning"
        )

        return redirect(
            url_for(
                "activities.chemical_requests"
            )
        )

    # ======================================================
    # GET CURRENT USER
    # ======================================================

    requester = session.get(
        "username",
        ""
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        try:

            # --------------------------------------------------
            # Requested quantity
            # --------------------------------------------------

            requested_quantity = (
                request.form.get(
                    "requested_quantity",
                    ""
                ).strip()
            )

            if not requested_quantity:

                flash(
                    "Please enter the requested quantity.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_form.html",
                    season=season,
                    programme=programme.to_dict(),
                    requested_quantity=""
                )

            # --------------------------------------------------
            # Notes
            # --------------------------------------------------

            notes = (
                request.form.get(
                    "notes",
                    ""
                ).strip()
            )

            # --------------------------------------------------
            # Generate Request ID
            # --------------------------------------------------

            request_id = (
                generate_chemical_request_id(
                    requests_df,
                    season
                )
            )

            # --------------------------------------------------
            # Request date
            # --------------------------------------------------

            request_date = pd.Timestamp.today()

            # --------------------------------------------------
            # Planned date
            # --------------------------------------------------

            planned_date = pd.to_datetime(
                programme.get(
                    "Planned Date"
                ),
                errors="coerce"
            )

            # --------------------------------------------------
            # Build request
            # --------------------------------------------------

            new_request = {

                # ======================================================
                # REQUEST IDENTIFICATION
                # ======================================================

                "Request ID": request_id,
                "Request Date": request_date,
                "Season": season,

                # ======================================================
                # REQUEST CLASSIFICATION
                # ======================================================

                "Request Type": "PROGRAMME",
                "Request Category": "HERBICIDE",

                # ======================================================
                # REQUESTER
                # ======================================================

                "Department": "Agriculture",
                "Requester": requester,

                # ======================================================
                # FIELD / PROGRAMME
                # ======================================================

                "Field": programme.get("Field", ""),
                "Programme ID": programme.get("Programme ID", ""),
                "Crop Type": programme.get("Crop Type", ""),
                "Crop Situation": programme.get("Crop Situation", ""),
                "Application Stage": programme.get("Application Stage", ""),

                # ======================================================
                # ITEM
                # ======================================================

                "Chemical": programme.get("Chemical", ""),
                "Item / Description": programme.get("Chemical", ""),
                "Specification": "",
                "Rate": programme.get("Rate", ""),
                "Rate Unit": programme.get("Rate Unit", ""),
                "Area (ha)": programme.get("Area (ha)", 0),

                # ======================================================
                # QUANTITY
                # ======================================================

                "Required Quantity": programme.get(
                    "Planned Quantity",
                    ""
                ),

                "Quantity Unit": programme.get(
                    "Quantity Unit",
                    ""
                ),

                "Requested Quantity": requested_quantity,

                # ======================================================
                # DATES
                # ======================================================

                "Planned Date": planned_date,
                "Required Date": planned_date,

                # ======================================================
                # PRIORITY
                # ======================================================

                "Urgency": "NORMAL",

                # ======================================================
                # JUSTIFICATION
                # ======================================================

                "Reason": "Planned herbicide programme",
                "Notes": notes,

                # ======================================================
                # AGRICULTURE APPROVAL
                # ======================================================

                "Status": "PENDING",
                "Approved By": "",
                "Approval Date": "",
                "Rejection Reason": "",

                # ======================================================
                # STORES
                # ======================================================

                "Stores Request ID": "",
                "Stores Request Date": "",

                # ======================================================
                # ISSUE
                # ======================================================

                "Issued Quantity": "",
                "Issue Date": ""
            }

            # --------------------------------------------------
            # Save
            # --------------------------------------------------

            requests_df = pd.concat(
                [
                    requests_df,
                    pd.DataFrame(
                        [new_request]
                    )
                ],
                ignore_index=True
            )

            save_chemical_requests(
                requests_df
            )

            flash(
                f"Chemical request {request_id} "
                "created successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "activities.chemical_requests"
                )
            )

        except Exception as e:

            flash(
                f"Error creating chemical request: {e}",
                "danger"
            )

    # ======================================================
    # GET FORM
    # ======================================================

    return render_template(
        "agriculture/chemical_request_form.html",
        season=season,
        programme=programme.to_dict(),
        requested_quantity=programme.get(
            "Planned Quantity",
            ""
        )
    )

@activity_bp.route(
    "/agriculture/chemical-request/new",
    methods=["GET", "POST"]
)
def create_operational_chemical_request():

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    from modules.season import get_active_season

    season = get_active_season()

    requests_df = load_chemical_requests()

    # ==========================================================
    # DEFAULT VALUES
    # ==========================================================

    form_data = {
        "field": "",
        "chemical": "",
        "rate": "",
        "rate_unit": "",
        "area": "",
        "required_quantity": "",
        "quantity_unit": "",
        "required_date": "",
        "urgency": "NORMAL",
        "reason": "",
        "notes": ""
    }

    # ==========================================================
    # POST
    # ==========================================================

    if request.method == "POST":

        try:

            # --------------------------------------------------
            # READ FORM
            # --------------------------------------------------

            form_data["field"] = (
                request.form.get("field", "")
                .strip()
            )

            form_data["chemical"] = (
                request.form.get("chemical", "")
                .strip()
            )

            form_data["rate"] = (
                request.form.get("rate", "")
                .strip()
            )

            form_data["rate_unit"] = (
                request.form.get("rate_unit", "")
                .strip()
            )

            form_data["area"] = (
                request.form.get("area", "")
                .strip()
            )

            form_data["required_quantity"] = (
                request.form.get(
                    "required_quantity",
                    ""
                )
                .strip()
            )

            form_data["quantity_unit"] = (
                request.form.get(
                    "quantity_unit",
                    ""
                )
                .strip()
            )

            form_data["required_date"] = (
                request.form.get(
                    "required_date",
                    ""
                )
                .strip()
            )

            form_data["urgency"] = (
                request.form.get(
                    "urgency",
                    "NORMAL"
                )
                .strip()
                .upper()
            )

            form_data["reason"] = (
                request.form.get(
                    "reason",
                    ""
                )
                .strip()
            )

            form_data["notes"] = (
                request.form.get(
                    "notes",
                    ""
                )
                .strip()
            )

            # --------------------------------------------------
            # VALIDATION
            # --------------------------------------------------

            if not form_data["field"]:

                flash(
                    "Please enter or select the field.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_operational_form.html",
                    season=season,
                    form_data=form_data
                )

            if not form_data["chemical"]:

                flash(
                    "Please enter or select the chemical.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_operational_form.html",
                    season=season,
                    form_data=form_data
                )

            if not form_data["required_quantity"]:

                flash(
                    "Please enter the requested quantity.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_operational_form.html",
                    season=season,
                    form_data=form_data
                )

            if not form_data["reason"]:

                flash(
                    "Please provide the reason for the request.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_operational_form.html",
                    season=season,
                    form_data=form_data
                )

            # --------------------------------------------------
            # VALIDATE URGENCY
            # --------------------------------------------------

            allowed_urgencies = [
                "NORMAL",
                "URGENT",
                "EMERGENCY"
            ]

            if form_data["urgency"] not in allowed_urgencies:

                form_data["urgency"] = "NORMAL"

            # --------------------------------------------------
            # DUPLICATE CHECK
            # --------------------------------------------------

            if operational_chemical_request_exists(
                requests_df,
                form_data["field"],
                form_data["chemical"],
                form_data["reason"]
            ):

                flash(
                    "An active operational chemical request "
                    "already exists for this field, chemical "
                    "and reason.",
                    "warning"
                )

                return render_template(
                    "agriculture/chemical_request_operational_form.html",
                    season=season,
                    form_data=form_data
                )

            # --------------------------------------------------
            # AREA
            # --------------------------------------------------

            area = pd.to_numeric(
                form_data["area"],
                errors="coerce"
            )

            if pd.isna(area):

                area = 0

            # --------------------------------------------------
            # REQUIRED DATE
            # --------------------------------------------------

            required_date = pd.to_datetime(
                form_data["required_date"],
                errors="coerce"
            )

            # --------------------------------------------------
            # REQUEST ID
            # --------------------------------------------------

            request_id = generate_chemical_request_id(
                requests_df,
                season
            )

            # --------------------------------------------------
            # REQUEST DATE
            # --------------------------------------------------

            request_date = pd.Timestamp.today()

            # --------------------------------------------------
            # NEW REQUEST
            # --------------------------------------------------

            new_request = {

                # ======================================================
                # REQUEST IDENTIFICATION
                # ======================================================

                "Request ID": request_id,
                "Request Date": request_date,
                "Season": season,

                # ======================================================
                # REQUEST CLASSIFICATION
                # ======================================================

                "Request Type": "OPERATIONAL",
                "Request Category": "HERBICIDE",

                # ======================================================
                # REQUESTER
                # ======================================================

                "Department": "Agriculture",
                "Requester": session.get("username", ""),

                # ======================================================
                # FIELD / PROGRAMME
                # ======================================================

                "Field": form_data["field"],
                "Programme ID": "",
                "Crop Type": "",
                "Crop Situation": "",
                "Application Stage": "",

                # ======================================================
                # ITEM
                # ======================================================

                "Chemical": form_data["chemical"],
                "Item / Description": form_data["chemical"],
                "Specification": "",
                "Rate": form_data["rate"],
                "Rate Unit": form_data["rate_unit"],
                "Area (ha)": area,

                # ======================================================
                # QUANTITY
                # ======================================================

                "Required Quantity": form_data["required_quantity"],
                "Quantity Unit": form_data["quantity_unit"],
                "Requested Quantity": form_data["required_quantity"],

                # ======================================================
                # DATES
                # ======================================================

                "Planned Date": "",
                "Required Date": required_date,

                # ======================================================
                # PRIORITY
                # ======================================================

                "Urgency": form_data["urgency"],

                # ======================================================
                # JUSTIFICATION
                # ======================================================

                "Reason": form_data["reason"],
                "Notes": form_data["notes"],

                # ======================================================
                # AGRICULTURE APPROVAL
                # ======================================================

                "Status": "PENDING",
                "Approved By": "",
                "Approval Date": "",
                "Rejection Reason": "",

                # ======================================================
                # STORES
                # ======================================================

                "Stores Request ID": "",
                "Stores Request Date": "",

                # ======================================================
                # ISSUE
                # ======================================================

                "Issued Quantity": "",
                "Issue Date": ""
            }

            # --------------------------------------------------
            # SAVE
            # --------------------------------------------------

            requests_df = pd.concat(
                [
                    requests_df,
                    pd.DataFrame(
                        [new_request]
                    )
                ],
                ignore_index=True
            )

            save_chemical_requests(
                requests_df
            )

            flash(
                f"Operational chemical request "
                f"{request_id} created successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "activities.chemical_requests"
                )
            )

        except Exception as e:

            flash(
                f"Error creating operational "
                f"chemical request: {e}",
                "danger"
            )

    # ==========================================================
    # GET
    # ==========================================================

    return render_template(
        "agriculture/chemical_request_operational_form.html",
        season=season,
        form_data=form_data
    )
# ==========================================================
# DUMMY HERBICIDE ROUTES
# ==========================================================
# Temporary routes so the Herbicide Menu can load while
# Chemical Request and Stores Issues modules are being built.
# ==========================================================


@activity_bp.route(
    "/agriculture/herbicide-stores-issues",
    methods=["GET"]
)
def herbicide_stores_issues():

    return render_template(
        "agriculture/herbicide_stores_issues.html"
    )


# modules/activities.py (or your designated module)
import numpy as np

FERTILIZER_FILE = "data/fertilizer_records.xlsx"

@activity_bp.route("/agriculture/fertilizer", methods=["GET", "POST"])
def fertilizer():
    if 'username' not in session:
        return redirect(url_for('login'))
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == "POST":
        data = {
            "Date": request.form.get("Date"),
            "Field": request.form.get("Field"),
            "Area (Ha)": request.form.get("Area (Ha)"),
            "Crop": request.form.get("Crop"),
            "DAP": request.form.get("DAP", type=float),
            "SA": request.form.get("SA", type=float),
            "MOP": request.form.get("MOP", type=float),
            "Zinc": request.form.get("Zinc", type=float),
            "UREA": request.form.get("UREA", type=float),
            "Mandays": request.form.get("Mandays", type=int),
            "Season": season
        }
        df = pd.read_excel(FERTILIZER_FILE) if os.path.exists(FERTILIZER_FILE) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_excel(FERTILIZER_FILE, index=False)
        flash("Fertilizer application saved successfully!", "success")
        return redirect(url_for('activities.fertilizer'))

    return render_template("agriculture/fertilizer.html", season=season)

@activity_bp.route("/agriculture/fertilizer-report")
def fertilizer_report():
    try:
        from modules.season import get_active_season
        import numpy as np

        season = get_active_season()
        field_filter = request.args.get("field")
        fert_filter = request.args.get("fertilizer")

        if not os.path.exists(FERTILIZER_FILE):
            flash("No fertilizer records found.", "warning")
            return render_template("agriculture/fertilizer_report.html", records=[], season=season,
                                   fields=[], fertilizers=[], totals={})

        df = pd.read_excel(FERTILIZER_FILE)
        df = df[df["Season"] == season] if "Season" in df.columns else df

        # Apply filters
        if field_filter:
            df = df[df["Field"] == field_filter]
        if fert_filter and fert_filter in df.columns:
            df = df[df[fert_filter] > 0]

        fields = sorted(df["Field"].dropna().unique().tolist())
        fertilizer_cols = ["DAP", "SA", "MOP", "Zinc", "UREA"]

        # Calculate totals
        # Totals - force float()
        totals = {
            col: float(round(df[col].sum(), 2))
            for col in fertilizer_cols if col in df.columns
        }

        # Records - force Python-native types
        records = df.to_dict(orient="records")
        for record in records:
            for k, v in record.items():
                if isinstance(v, (np.integer, np.int64, np.int32)):
                    record[k] = int(v)
                elif isinstance(v, (np.floating, np.float64, np.float32)):
                    record[k] = float(v)
                elif pd.isna(v):
                    record[k] = None

        return render_template("agriculture/fertilizer_report.html",
                               records=records,
                               season=season,
                               fields=fields,
                               fertilizers=fertilizer_cols,
                               totals=totals,
                               selected_field=field_filter,
                               selected_fertilizer=fert_filter)

    except Exception as e:
        flash(f"Error loading report: {e}", "danger")
        return render_template("agriculture/fertilizer_report.html",
                               records=[], season="N/A", fields=[], fertilizers=[], totals={})

# ==========================================================
# FERTILIZER APPLICATION REMINDERS
# ==========================================================

FERTILIZER_SCHEDULE_FILE = "data/fertilizer_schedule.xlsx"


# ==========================================================
# WHOLE-BAG NORMALISATION
# ==========================================================

def whole_bags(value):
    """
    Convert fertilizer quantities to whole bags.

    DCGL whole-bag rule:

        6.08 -> 6
        6.49 -> 6
        6.50 -> 6
        15.00 -> 15

    Used for:
        - planned quantity
        - actual quantity
        - balance
        - display
        - status calculations
    """

    try:
        value = float(value or 0)

    except (
        TypeError,
        ValueError
    ):
        return 0

    if value <= 0:
        return 0

    return int(value + 0.5)


# ==========================================================
# FERTILIZER NAME NORMALISATION
# ==========================================================

def normalize_fertilizer_name(name):
    """
    Normalise fertilizer names.

    Zinc / ZINC -> ZINC
    """

    name = str(
        name or ""
    ).strip().upper()

    if name == "ZINC":
        return "ZINC"

    return name


# ==========================================================
# OPERATION NORMALISATION
# ==========================================================

def normalize_operation_name(operation):
    """
    Normalise fertilizer programme operation names.

    This is used when identifying duplicate programme
    records and when determining Top Dressing stages.
    """

    operation = str(
        operation or ""
    ).strip().upper()

    if (
        "BASAL" in operation
    ):
        return "BASAL APPLICATION"

    if (
        "TOP DRESSING 1" in operation
        or
        "FIRST TOP" in operation
    ):
        return "TOP DRESSING 1"

    if (
        "TOP DRESSING 2" in operation
        or
        "SECOND TOP" in operation
    ):
        return "TOP DRESSING 2"

    return operation


# ==========================================================
# ACTUAL FERTILIZER APPLICATIONS
# ==========================================================

def get_actual_fertilizer_applications(
    actual_df,
    field,
    fertilizer
):
    """
    Return actual applications for ONE field and ONE fertilizer
    in chronological order.

    Multiple records on the same date are combined.

    UREA and SA are completely independent.
    """

    if (
        actual_df is None
        or actual_df.empty
    ):
        return []

    field = str(
        field or ""
    ).strip().upper()

    fertilizer = normalize_fertilizer_name(
        fertilizer
    )

    if "Field" not in actual_df.columns:
        return []

    # ------------------------------------------------------
    # FIND ACTUAL FERTILIZER COLUMN
    # ------------------------------------------------------

    actual_column = None

    for column in actual_df.columns:

        if normalize_fertilizer_name(
            column
        ) == fertilizer:

            actual_column = column
            break

    if actual_column is None:
        return []

    temp = actual_df.copy()

    # ------------------------------------------------------
    # NORMALISE FIELD
    # ------------------------------------------------------

    temp["Field"] = (
        temp["Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # ------------------------------------------------------
    # NORMALISE DATE
    # ------------------------------------------------------

    if "Date" not in temp.columns:
        return []

    temp["_ApplicationDate"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    # ------------------------------------------------------
    # NORMALISE QUANTITY
    # ------------------------------------------------------

    temp["_ActualQuantity"] = pd.to_numeric(
        temp[actual_column],
        errors="coerce"
    ).fillna(0)

    # ------------------------------------------------------
    # FILTER
    # ------------------------------------------------------

    temp = temp[
        (temp["Field"] == field)
        &
        (temp["_ActualQuantity"] > 0)
        &
        (temp["_ApplicationDate"].notna())
    ].copy()

    if temp.empty:
        return []

    # ------------------------------------------------------
    # COMBINE MULTIPLE APPLICATIONS ON SAME DATE
    # ------------------------------------------------------

    grouped = (
        temp
        .groupby(
            "_ApplicationDate",
            as_index=False
        )["_ActualQuantity"]
        .sum()
        .sort_values(
            "_ApplicationDate"
        )
    )

    applications = []

    for _, row in grouped.iterrows():

        quantity = whole_bags(
            row["_ActualQuantity"]
        )

        if quantity <= 0:
            continue

        applications.append(
            {
                "date":
                    row["_ApplicationDate"],

                "quantity":
                    quantity
            }
        )

    return applications


# ==========================================================
# DATE HELPERS
# ==========================================================

def get_top_dressing_date(
    basal_date,
    days=28
):
    """
    Return a date a specified number of days after
    the actual Basal date.
    """

    if basal_date is None:
        return None

    try:

        basal_date = pd.to_datetime(
            basal_date
        )

        return (
            basal_date
            + pd.Timedelta(
                days=days
            )
        )

    except Exception:

        return None


def get_next_top_dressing_date(
    actual_first_date
):
    """
    Top Dressing 2 is 28 days after the ACTUAL
    Top Dressing 1 application.

    UREA and SA are calculated independently.
    """

    if actual_first_date is None:
        return None

    try:

        actual_first_date = pd.to_datetime(
            actual_first_date
        )

        return (
            actual_first_date
            + pd.Timedelta(
                days=28
            )
        )

    except Exception:

        return None


# ==========================================================
# GET ACTUAL BASAL DATE FOR A FIELD
# ==========================================================

def get_field_basal_date(
    actual_df,
    field
):
    """
    Find the ACTUAL BASAL fertilizer date.

    Basal fertilizers:
        DAP
        MOP
        ZINC

    The earliest actual basal application for the field
    becomes the Basal anchor.

    Planned Top Dressing dates are never used.
    """

    if (
        actual_df is None
        or actual_df.empty
    ):
        return None

    field = str(
        field or ""
    ).strip().upper()

    if "Field" not in actual_df.columns:
        return None

    temp = actual_df.copy()

    temp["Field"] = (
        temp["Field"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if "Date" not in temp.columns:
        return None

    temp["_ApplicationDate"] = pd.to_datetime(
        temp["Date"],
        errors="coerce"
    )

    temp = temp[
        temp["Field"] == field
    ].copy()

    if temp.empty:
        return None

    basal_dates = []

    for fertilizer_column in [
        "DAP",
        "MOP",
        "ZINC",
        "Zinc"
    ]:

        if fertilizer_column not in temp.columns:
            continue

        quantities = pd.to_numeric(
            temp[fertilizer_column],
            errors="coerce"
        ).fillna(0)

        valid_dates = temp.loc[
            (
                quantities > 0
            )
            &
            (
                temp["_ApplicationDate"].notna()
            ),
            "_ApplicationDate"
        ]

        if not valid_dates.empty:

            basal_dates.extend(
                valid_dates.tolist()
            )

    if not basal_dates:
        return None

    return min(
        basal_dates
    )


# ==========================================================
# GET ACTUAL TOP-DRESSING APPLICATIONS
# ==========================================================

def get_top_dressing_applications(
    actual_applications,
    basal_date
):
    """
    Determine actual Top Dressing applications strictly from
    ACTUAL application dates.

    DCGL RULE:

        Basal
           ↓
        First actual fertilizer application after Basal
           = TOP DRESSING 1
           ↓
        Second actual fertilizer application after Basal
           = TOP DRESSING 2

    IMPORTANT:
        Planned dates are NEVER used here.

    Example:

        Basal actual       = 2026-07-25
        Planned Top 1      = 2026-08-22
        Actual Top 1       = 2026-09-30

        Result:

        Top 1 actual       = 2026-09-30
        Top 2 planned      = 2026-10-28

    UREA and SA are processed independently.
    """

    if not actual_applications:
        return []

    if basal_date is None:
        return []

    try:

        basal_date = pd.to_datetime(
            basal_date
        )

    except Exception:

        return []

    valid_applications = []

    for application in actual_applications:

        if not isinstance(
            application,
            dict
        ):
            continue

        application_date = application.get(
            "date"
        )

        if application_date is None:
            continue

        try:

            application_date = pd.to_datetime(
                application_date
            )

        except Exception:

            continue

        # --------------------------------------------------
        # ONLY ACTUAL APPLICATIONS AFTER BASAL
        # --------------------------------------------------

        if application_date <= basal_date:
            continue

        try:

            quantity = whole_bags(
                application.get(
                    "quantity",
                    0
                )
            )

        except Exception:

            quantity = 0

        if quantity <= 0:
            continue

        valid_applications.append({

            "date":
                application_date,

            "quantity":
                quantity
        })

    # ------------------------------------------------------
    # SORT ONLY BY ACTUAL APPLICATION DATE
    # ------------------------------------------------------

    valid_applications.sort(
        key=lambda x: x["date"]
    )

    return valid_applications


# ==========================================================
# FERTILIZER REMINDER STATUS
# ==========================================================

def get_fertilizer_reminder_status(
    planned_date
):
    """
    Determine reminder status from today's date.
    """

    if not planned_date:
        return "NO DATE"

    try:

        planned_date = (
            pd.to_datetime(
                planned_date
            ).date()
        )

        today = (
            pd.Timestamp
            .today()
            .date()
        )

        days = (
            planned_date - today
        ).days

        if days < 0:
            return "OVERDUE"

        elif days == 0:
            return "DUE TODAY"

        elif days <= 7:
            return "DUE SOON"

        else:
            return "SCHEDULED"

    except Exception:

        return "NO DATE"

# ==========================================================
# FERTILIZER SCHEDULE SUMMARY
# ==========================================================

def get_fertilizer_schedule_summary(season):
    """
    Return fertilizer schedule card values.

    IMPORTANT:

    This function does NOT independently calculate
    fertilizer status.

    It uses the exact same processed records used
    by the Fertilizer Schedule page.

    Therefore the Dashboard and Fertilizer Schedule
    page always show the same numbers.
    """

    summary = {
        "overdue": 0,
        "due_today": 0,
        "due_soon": 0,
        "scheduled": 0,
        "total": 0,
        "applied": 0,
        "programme_exists": False
    }

    # ======================================================
    # GET THE SAME PROCESSED RECORDS
    # ======================================================

    records = get_processed_fertilizer_schedule(
        season
    )

    if not records:
        return summary

    summary["programme_exists"] = True

    # ======================================================
    # COUNT THE EXACT SAME STATUSES
    # ======================================================

    for record in records:

        status = str(
            record.get(
                "Status",
                ""
            )
        ).strip().upper()

        if status == "OVERDUE":

            summary["overdue"] += 1

        elif status == "DUE TODAY":

            summary["due_today"] += 1

        elif status == "DUE SOON":

            summary["due_soon"] += 1

        elif status == "SCHEDULED":

            summary["scheduled"] += 1

        elif status == "APPLIED":

            summary["applied"] += 1

    # ======================================================
    # OUTSTANDING APPLICATIONS
    # ======================================================

    summary["total"] = (
        summary["overdue"]
        +
        summary["due_today"]
        +
        summary["due_soon"]
        +
        summary["scheduled"]
    )

    return summary

# ==========================================================
# APPLY RECORD RESULT
# ==========================================================

def update_fertilizer_record(
    record,
    planned_bags,
    actual_bags,
    actual_date=None
):
    """
    Apply planned quantity, actual quantity,
    balance, date and status to ONE schedule record.

    Existing status values are deliberately overwritten.
    This prevents old APPLIED/PARTIAL values from remaining
    in duplicate or regenerated records.
    """

    planned_bags = whole_bags(
        planned_bags
    )

    actual_bags = whole_bags(
        actual_bags
    )

    balance = whole_bags(
        max(
            planned_bags - actual_bags,
            0
        )
    )

    record[
        "Planned Quantity (bags)"
    ] = planned_bags

    record[
        "Actual Quantity (bags)"
    ] = actual_bags

    record[
        "Balance (bags)"
    ] = balance

    # ------------------------------------------------------
    # ACTUAL DATE
    # ------------------------------------------------------

    if actual_date is not None:

        try:

            actual_date = pd.to_datetime(
                actual_date
            )

            record[
                "Actual Date"
            ] = actual_date.strftime(
                "%Y-%m-%d"
            )

        except Exception:

            record[
                "Actual Date"
            ] = None

    else:

        record[
            "Actual Date"
        ] = None

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    if planned_bags <= 0:

        if actual_bags > 0:

            record[
                "Status"
            ] = "APPLIED"

        else:

            record[
                "Status"
            ] = "NOT REQUIRED"

    elif actual_bags >= planned_bags:

        record[
            "Status"
        ] = "APPLIED"

    elif actual_bags > 0:

        record[
            "Status"
        ] = "PARTIAL"

    else:

        record[
            "Status"
        ] = get_fertilizer_reminder_status(
            record.get(
                "Planned Date"
            )
        )

    # ------------------------------------------------------
    # BALANCE DISPLAY
    # ------------------------------------------------------

    if balance <= 0:

        record[
            "Balance Display"
        ] = "Complete"

    else:

        record[
            "Balance Display"
        ] = (
            f"{balance} bags remaining"
        )


# ==========================================================
# REMOVE DUPLICATE PROGRAMME RECORDS
# ==========================================================

def deduplicate_fertilizer_schedule(
    schedule_df
):
    """
    Remove duplicate generated programme records.

    A fertilizer programme must contain only ONE record
    for each:

        Season
        Field
        Operation
        Fertilizer

    Example:

        DG01001 + First Top Dressing + UREA
        DG01001 + First Top Dressing + SA
        DG01001 + Second Top Dressing + UREA
        DG01001 + Second Top Dressing + SA

    must each exist only once.

    The LAST occurrence is retained because a regenerated
    programme is normally the newest programme record.

    This prevents old programme rows from appearing alongside
    newly generated rows.
    """

    if (
        schedule_df is None
        or schedule_df.empty
    ):
        return schedule_df

    df = schedule_df.copy()

    # ------------------------------------------------------
    # NORMALISE KEY COLUMNS
    # ------------------------------------------------------

    if "Season" in df.columns:

        df["_SeasonKey"] = (
            df["Season"]
            .astype(str)
            .str.strip()
        )

    else:

        df["_SeasonKey"] = ""

    if "Field" in df.columns:

        df["_FieldKey"] = (
            df["Field"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    else:

        df["_FieldKey"] = ""

    if "Operation" in df.columns:

        df["_OperationKey"] = (
            df["Operation"]
            .apply(
                normalize_operation_name
            )
        )

    else:

        df["_OperationKey"] = ""

    if "Fertilizer" in df.columns:

        df["_FertilizerKey"] = (
            df["Fertilizer"]
            .apply(
                normalize_fertilizer_name
            )
        )

    else:

        df["_FertilizerKey"] = ""

    # ------------------------------------------------------
    # DROP DUPLICATES
    # ------------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "_SeasonKey",
            "_FieldKey",
            "_OperationKey",
            "_FertilizerKey"
        ],
        keep="last"
    ).copy()

    # ------------------------------------------------------
    # REMOVE TEMPORARY COLUMNS
    # ------------------------------------------------------

    df.drop(
        columns=[
            "_SeasonKey",
            "_FieldKey",
            "_OperationKey",
            "_FertilizerKey"
        ],
        inplace=True,
        errors="ignore"
    )

    return df.reset_index(
        drop=True
    )


# ==========================================================
# FERTILIZER SCHEDULE
# ==========================================================

@activity_bp.route(
    "/agriculture/fertilizer-schedule",
    methods=["GET", "POST"]
)
def fertilizer_schedule():

    if "username" not in session:
        return redirect(
            url_for("login")
        )

    from modules.season import get_active_season

    season = get_active_season()

    # ======================================================
    # SAVE NEW FERTILIZER PLAN
    # ======================================================

    if request.method == "POST":

        data = {

            "Season":
                season,

            "Field":
                request.form.get(
                    "Field"
                ),

            "Area (Ha)":
                request.form.get(
                    "Area (Ha)",
                    type=float
                ),

            "Crop":
                request.form.get(
                    "Crop"
                ),

            "Fertilizer":
                normalize_fertilizer_name(
                    request.form.get(
                        "Fertilizer"
                    )
                ),

            "Planned Date":
                request.form.get(
                    "Planned Date"
                ),

            "Rate (bags/Ha)":
                request.form.get(
                    "Rate (bags/Ha)",
                    type=float
                ),

            "Planned Quantity (bags)":
                request.form.get(
                    "Planned Quantity (bags)",
                    type=float
                ),

            "Status":
                "PLANNED",

            "Actual Date":
                None,

            "Notes":
                request.form.get(
                    "Notes"
                )
        }

        # --------------------------------------------------
        # LOAD EXISTING PROGRAMME
        # --------------------------------------------------

        if os.path.exists(
            FERTILIZER_SCHEDULE_FILE
        ):

            df = pd.read_excel(
                FERTILIZER_SCHEDULE_FILE
            )

        else:

            df = pd.DataFrame()

        # --------------------------------------------------
        # ADD NEW RECORD
        # --------------------------------------------------

        df = pd.concat(
            [
                df,
                pd.DataFrame(
                    [data]
                )
            ],
            ignore_index=True
        )

        # --------------------------------------------------
        # REMOVE DUPLICATE PROGRAMME ROWS
        # --------------------------------------------------

        df = deduplicate_fertilizer_schedule(
            df
        )

        # --------------------------------------------------
        # SAVE PROGRAMME
        # --------------------------------------------------

        df.to_excel(
            FERTILIZER_SCHEDULE_FILE,
            index=False
        )

        flash(
            "Fertilizer application reminder created successfully!",
            "success"
        )

        return redirect(
            url_for(
                "activities.fertilizer_schedule"
            )
        )

    # ======================================================
    # GET PROCESSED FERTILIZER PROGRAMME
    # ======================================================
    #
    # IMPORTANT:
    #
    # This is now the SINGLE processing source for:
    #
    #     - Fertilizer Schedule page
    #     - Fertilizer Schedule cards
    #     - Main Dashboard
    #
    # It reads the existing programme and actual
    # fertilizer records.
    #
    # It does NOT generate a new programme.
    #
    # Therefore applying fertilizer does NOT require
    # regenerating the fertilizer programme.
    #
    # ======================================================

    reminders = get_processed_fertilizer_schedule(
        season
    )

    # ======================================================
    # REMINDER SUMMARY
    # ======================================================
    #
    # The cards are calculated from the SAME records
    # displayed in the fertilizer schedule table.
    #
    # ======================================================

    reminder_summary = {

        "overdue": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "OVERDUE"
        ),

        "due_today": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "DUE TODAY"
        ),

        "due_soon": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "DUE SOON"
        ),

        "scheduled": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "SCHEDULED"
        ),

        "partial": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "PARTIAL"
        ),

        "applied": sum(
            1
            for record in reminders
            if str(
                record.get(
                    "Status",
                    ""
                )
            ).strip().upper()
            == "APPLIED"
        )
    }

    # ======================================================
    # SORT REMINDERS
    # ======================================================

    status_order = {

        "OVERDUE": 0,
        "DUE TODAY": 1,
        "DUE SOON": 2,
        "SCHEDULED": 3,
        "PARTIAL": 4,
        "APPLIED": 5,
        "NOT REQUIRED": 6,
        "NO DATE": 7
    }

    # ======================================================
    # APPLICATION SEQUENCE
    # ======================================================

    application_order = {

        "BASAL DRESSING": 1,
        "BASAL APPLICATION": 1,

        "TOP DRESSING 1": 2,

        "TOP DRESSING 2": 3
    }

    # ======================================================
    # FERTILIZER SEQUENCE
    # ======================================================

    fertilizer_order = {

        "DAP": 1,
        "MOP": 2,
        "ZINC": 3,
        "SA": 4,
        "UREA": 5
    }

    def fertilizer_sort_key(record):

        estate = str(
            record.get(
                "Estate",
                ""
            )
        ).strip().upper()

        field = str(
            record.get(
                "Field",
                ""
            )
        ).strip().upper()

        operation = str(
            record.get(
                "Operation",
                ""
            )
        ).strip().upper()

        fertilizer = str(
            record.get(
                "Fertilizer",
                ""
            )
        ).strip().upper()

        return (

            # Estate
            estate,

            # Field
            field,

            # Basal → Top 1 → Top 2
            application_order.get(
                operation,
                99
            ),

            # DAP → MOP → Zinc → SA → UREA
            fertilizer_order.get(
                fertilizer,
                99
            ),

            # Date only as a final tie-breaker
            str(
                record.get(
                    "Planned Date",
                    ""
                )
            )

        )

    reminders.sort(
        key=fertilizer_sort_key
    )

    # ======================================================
    # RENDER FERTILIZER SCHEDULE
    # ======================================================

    return render_template(
        "agriculture/fertilizer_schedule.html",
        season=season,
        reminders=reminders,
        reminder_summary=reminder_summary
    )

# ==========================================================
# PROCESSED FERTILIZER SCHEDULE
# ==========================================================

def get_processed_fertilizer_schedule(season):
    """
    Process the fertilizer programme for a season.

    This is the SINGLE source of truth for fertilizer
    schedule records and their statuses.

    Used by:
        - Fertilizer Schedule page
        - Main Dashboard

    The function does NOT generate a programme.

    It reads:
        - fertilizer_schedule.xlsx
        - fertilizer_records.xlsx

    ACTUAL DATE / AGRONOMIC ANCHOR RULES:

        1. FIRST actual Basal application is the Basal anchor.

        2. Planned Top Dressing 1:
               Actual Basal + 28 days

           If there is no actual Basal:
               Existing planned Top 1 date is retained.

        3. If actual Top Dressing 1 exists:
               Planned Top Dressing 2
               = Actual Top Dressing 1 + 28 days

        4. If actual Top Dressing 1 does NOT exist:
               Planned Top Dressing 2
               = Planned Top Dressing 1 + 28 days

        5. A later Basal application NEVER resets the
           Basal anchor.

    IMPORTANT:

        UREA and SA actual applications are processed
        independently.

        The overall Top Dressing 1 date is the EARLIEST
        actual UREA/SA application after the first actual
        Basal application.

        This ensures the fertilizer programme follows
        actual crop nutrition timing rather than simply
        adding 56 days to the original Basal date.
    """

    records = []

    # ======================================================
    # CHECK PROGRAMME FILE
    # ======================================================

    if not os.path.exists(
        FERTILIZER_SCHEDULE_FILE
    ):
        return records

    # ======================================================
    # LOAD PROGRAMME
    # ======================================================

    schedule_df = pd.read_excel(
        FERTILIZER_SCHEDULE_FILE
    )

    if schedule_df.empty:
        return records

    # ======================================================
    # CLEAN COLUMN NAMES
    # ======================================================

    schedule_df.columns = (
        schedule_df.columns
        .astype(str)
        .str.strip()
    )

    # ======================================================
    # FILTER SEASON
    # ======================================================

    if "Season" in schedule_df.columns:

        schedule_df = schedule_df[
            schedule_df["Season"]
            .astype(str)
            .str.strip()
            ==
            str(season).strip()
        ].copy()

    if schedule_df.empty:
        return records

    # ======================================================
    # REMOVE DUPLICATES
    # ======================================================

    schedule_df = deduplicate_fertilizer_schedule(
        schedule_df
    )

    if schedule_df.empty:
        return records

    # ======================================================
    # LOAD ACTUAL FERTILIZER APPLICATIONS
    # ======================================================

    actual_df = pd.DataFrame()

    if os.path.exists(FERTILIZER_FILE):

        actual_df = pd.read_excel(
            FERTILIZER_FILE
        )

        # --------------------------------------------------
        # FILTER SEASON
        # --------------------------------------------------

        if "Season" in actual_df.columns:

            actual_df = actual_df[
                actual_df["Season"]
                .astype(str)
                .str.strip()
                ==
                str(season).strip()
            ].copy()

        # --------------------------------------------------
        # NORMALISE FIELD
        # --------------------------------------------------

        if "Field" in actual_df.columns:

            actual_df["Field"] = (
                actual_df["Field"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

        # --------------------------------------------------
        # NORMALISE DATE
        # --------------------------------------------------

        if "Date" in actual_df.columns:

            actual_df["_ApplicationDate"] = (
                pd.to_datetime(
                    actual_df["Date"],
                    errors="coerce"
                )
            )

        else:

            actual_df["_ApplicationDate"] = pd.NaT

    # ======================================================
    # CONVERT PROGRAMME TO RECORDS
    # ======================================================

    records = schedule_df.to_dict(
        orient="records"
    )

    # ======================================================
    # NORMALISE RECORDS
    # ======================================================

    for record in records:

        record["Field"] = (
            str(
                record.get(
                    "Field",
                    ""
                )
            )
            .strip()
            .upper()
        )

        record["Fertilizer"] = (
            normalize_fertilizer_name(
                record.get(
                    "Fertilizer",
                    ""
                )
            )
        )

        record["Operation"] = (
            normalize_operation_name(
                record.get(
                    "Operation",
                    ""
                )
            )
        )

    # ======================================================
    # GROUP BY FIELD + FERTILIZER
    # ======================================================

    programme_groups = {}

    for index, record in enumerate(records):

        field = record.get(
            "Field",
            ""
        )

        fertilizer = record.get(
            "Fertilizer",
            ""
        )

        group_key = (
            field,
            fertilizer
        )

        if group_key not in programme_groups:

            programme_groups[group_key] = []

        programme_groups[group_key].append(
            index
        )

    # ======================================================
    # PROCESS EACH FIELD + FERTILIZER
    # ======================================================

    for (
        field,
        fertilizer
    ), group_indexes in programme_groups.items():

        if not group_indexes:
            continue

        group_records = [
            records[index]
            for index in group_indexes
        ]

        # ==================================================
        # ACTUAL APPLICATIONS
        # ==================================================

        actual_applications = (
            get_actual_fertilizer_applications(
                actual_df,
                field,
                fertilizer
            )
        )

        # ==================================================
        # FIRST ACTUAL BASAL DATE
        # ==================================================
        #
        # IMPORTANT:
        #
        # This returns the EARLIEST actual Basal
        # application across:
        #
        #     DAP
        #     MOP
        #     ZINC
        #
        # Therefore:
        #
        # DAP = 25/07
        # MOP = 09/09
        #
        # Basal anchor remains:
        #
        #     25/07
        #
        # The later MOP application does NOT reset
        # the nutrition clock.
        #
        # ==================================================

        basal_date = get_field_basal_date(
            actual_df,
            field
        )

        if basal_date is not None:

            basal_date = pd.to_datetime(
                basal_date,
                errors="coerce"
            )

            if pd.isna(
                basal_date
            ):

                basal_date = None

        # ==================================================
        # GET ACTUAL UREA / SA APPLICATIONS
        # ==================================================
        #
        # We calculate these separately because UREA
        # and SA are independent fertilizers.
        #
        # The first actual application of either one
        # becomes the overall actual Top Dressing 1 date.
        #
        # ==================================================

        actual_urea_applications = []

        actual_sa_applications = []

        if fertilizer == "UREA":

            actual_urea_applications = (
                get_top_dressing_applications(
                    actual_applications,
                    basal_date
                )
            )

        elif fertilizer == "SA":

            actual_sa_applications = (
                get_top_dressing_applications(
                    actual_applications,
                    basal_date
                )
            )

        # ==================================================
        # FIND OVERALL ACTUAL TOP DRESSING 1
        # ==================================================
        #
        # Because UREA and SA are processed independently,
        # we must look at BOTH fertilizers for the field.
        #
        # Example:
        #
        # UREA actual Top 1 = 09/09
        # SA   actual Top 1 = 09/09
        #
        # actual_top_1_date = 09/09
        #
        # If:
        #
        # UREA = 10/09
        # SA   = 09/09
        #
        # actual_top_1_date = 09/09
        #
        # ==================================================

        actual_top_1_candidates = []

        if fertilizer in (
            "UREA",
            "SA"
        ):

            # ------------------------------------------------
            # CURRENT FERTILIZER APPLICATIONS
            # ------------------------------------------------

            current_top_applications = (
                get_top_dressing_applications(
                    actual_applications,
                    basal_date
                )
            )

            if current_top_applications:

                actual_top_1_candidates.append(
                    current_top_applications[0]
                    .get("date")
                )

            # ------------------------------------------------
            # OTHER FERTILIZER
            # ------------------------------------------------

            other_fertilizer = (
                "SA"
                if fertilizer == "UREA"
                else "UREA"
            )

            other_applications = (
                get_actual_fertilizer_applications(
                    actual_df,
                    field,
                    other_fertilizer
                )
            )

            other_top_applications = (
                get_top_dressing_applications(
                    other_applications,
                    basal_date
                )
            )

            if other_top_applications:

                actual_top_1_candidates.append(
                    other_top_applications[0]
                    .get("date")
                )

        # --------------------------------------------------
        # CLEAN TOP 1 CANDIDATES
        # --------------------------------------------------

        actual_top_1_candidates = [

            pd.to_datetime(
                date,
                errors="coerce"
            )

            for date
            in actual_top_1_candidates

            if date is not None
        ]

        actual_top_1_candidates = [

            date

            for date
            in actual_top_1_candidates

            if pd.notna(date)
        ]

        if actual_top_1_candidates:

            actual_top_1_date = min(
                actual_top_1_candidates
            )

        else:

            actual_top_1_date = None

        # ==================================================
        # IDENTIFY PROGRAMME STAGES
        # ==================================================

        basal_indexes = []

        top1_index = None
        top2_index = None

        other_indexes = []

        for index in group_indexes:

            operation = (
                normalize_operation_name(
                    records[index].get(
                        "Operation",
                        ""
                    )
                )
            )

            if operation == "BASAL APPLICATION":

                basal_indexes.append(
                    index
                )

            elif operation == "TOP DRESSING 1":

                top1_index = index

            elif operation == "TOP DRESSING 2":

                top2_index = index

            else:

                other_indexes.append(
                    index
                )

        # ==================================================
        # STAGE ORDER
        # ==================================================

        stage_indexes = []

        for index in basal_indexes:

            stage_indexes.append(
                index
            )

        if top1_index is not None:

            stage_indexes.append(
                top1_index
            )

        if top2_index is not None:

            stage_indexes.append(
                top2_index
            )

        for index in other_indexes:

            stage_indexes.append(
                index
            )

        # ==================================================
        # UREA / SA TOP DRESSING ALLOCATION
        # ==================================================

        planned_top1 = 0
        planned_top2 = 0

        if fertilizer in (
            "UREA",
            "SA"
        ):

            # ----------------------------------------------
            # PROGRAMME AREA
            # ----------------------------------------------

            area = 0

            for record in group_records:

                try:

                    area = float(
                        record.get(
                            "Area (Ha)",
                            0
                        )
                        or 0
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    area = 0

                if area > 0:
                    break

            programme_area = area

            if (
                area > 3.0
                and area < 3.51
            ):

                programme_area = 3.0

            elif area > 0:

                programme_area = round(
                    area,
                    3
                )

            # ----------------------------------------------
            # TOP DRESSING RATES
            # ----------------------------------------------

            top1_rate = 0
            top2_rate = 0

            for record in group_records:

                operation = (
                    normalize_operation_name(
                        record.get(
                            "Operation",
                            ""
                        )
                    )
                )

                try:

                    rate = float(
                        record.get(
                            "Rate (bags/Ha)",
                            0
                        )
                        or 0
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    rate = 0

                if operation == "TOP DRESSING 1":

                    top1_rate = rate

                elif operation == "TOP DRESSING 2":

                    top2_rate = rate

            total_rate = (
                top1_rate
                +
                top2_rate
            )

            # ----------------------------------------------
            # TOTAL REQUIREMENT
            # ----------------------------------------------

            if (
                programme_area > 0
                and total_rate > 0
            ):

                total_requirement = (
                    whole_bags(
                        programme_area
                        *
                        total_rate
                    )
                )

            else:

                total_requirement = 0

            # ----------------------------------------------
            # DEFAULT SPLIT
            # ----------------------------------------------

            if total_requirement > 0:

                fertilizer_top1 = (
                    total_requirement // 2
                )

                fertilizer_top2 = (
                    total_requirement
                    -
                    fertilizer_top1
                )

            else:

                fertilizer_top1 = 0
                fertilizer_top2 = 0

            # ----------------------------------------------
            # FIRST ACTUAL APPLICATION DEFINES TOP 1
            # ----------------------------------------------
            #
            # IMPORTANT:
            #
            # The first actual application is used only
            # for quantity allocation.
            #
            # The actual date is separately used above
            # to determine the rolling Top 2 date.
            #
            # ----------------------------------------------

            if actual_applications:

                first_actual_quantity = (
                    whole_bags(
                        actual_applications[0]
                        .get(
                            "quantity",
                            0
                        )
                    )
                )

                if (
                    first_actual_quantity > 0
                    and
                    first_actual_quantity
                    <
                    total_requirement
                ):

                    fertilizer_top1 = (
                        first_actual_quantity
                    )

                    fertilizer_top2 = (
                        total_requirement
                        -
                        fertilizer_top1
                    )

            planned_top1 = whole_bags(
                fertilizer_top1
            )

            planned_top2 = whole_bags(
                fertilizer_top2
            )

        # ==================================================
        # UPDATE PROGRAMME STAGES
        # ==================================================

        for (
            stage_number,
            index
        ) in enumerate(stage_indexes):

            record = records[index]

            operation = (
                normalize_operation_name(
                    record.get(
                        "Operation",
                        ""
                    )
                )
            )

            # ----------------------------------------------
            # PLANNED QUANTITY
            # ----------------------------------------------

            if (
                fertilizer in (
                    "UREA",
                    "SA"
                )
                and
                operation
                ==
                "TOP DRESSING 1"
            ):

                planned = whole_bags(
                    planned_top1
                )

            elif (
                fertilizer in (
                    "UREA",
                    "SA"
                )
                and
                operation
                ==
                "TOP DRESSING 2"
            ):

                planned = whole_bags(
                    planned_top2
                )

            else:

                planned = whole_bags(
                    record.get(
                        "Planned Quantity (bags)",
                        0
                    )
                )

            # ==================================================
            # ACTUAL APPLICATION
            # ==================================================

            if (
                operation
                ==
                "BASAL APPLICATION"
                and
                top1_index is None
                and
                top2_index is None
            ):

                # ------------------------------------------
                # BASAL-ONLY FERTILIZER
                #
                # ALL actual applications are cumulative.
                # ------------------------------------------

                actual = whole_bags(
                    sum(
                        whole_bags(
                            application.get(
                                "quantity",
                                0
                            )
                        )
                        for application
                        in actual_applications
                    )
                )

                if actual_applications:

                    # Last actual date is displayed for
                    # the final cumulative Basal record.
                    actual_date = (
                        actual_applications[-1]
                        .get(
                            "date"
                        )
                    )

                else:

                    actual_date = None

            else:

                # ------------------------------------------
                # STAGE-BY-STAGE APPLICATION
                # ------------------------------------------

                if (
                    stage_number
                    <
                    len(actual_applications)
                ):

                    actual_application = (
                        actual_applications[
                            stage_number
                        ]
                    )

                    actual = whole_bags(
                        actual_application.get(
                            "quantity",
                            0
                        )
                    )

                    actual_date = (
                        actual_application.get(
                            "date"
                        )
                    )

                else:

                    actual = 0
                    actual_date = None

            # ----------------------------------------------
            # UPDATE STATUS
            # ----------------------------------------------

            update_fertilizer_record(
                record,
                planned,
                actual,
                actual_date
            )

        # ==================================================
        # TOP DRESSING 1 DATE
        # ==================================================
        #
        # ACTUAL BASAL controls the first planned
        # Top Dressing date.
        #
        # Example:
        #
        # Actual Basal = 25/07
        #
        # Planned Top 1 = 22/08
        #
        # ==================================================

        if top1_index is not None:

            top1_record = records[
                top1_index
            ]

            if basal_date is not None:

                planned_top1_date = (
                    pd.to_datetime(
                        basal_date
                    )
                    +
                    pd.Timedelta(
                        days=28
                    )
                )

                top1_record[
                    "Planned Date"
                ] = (
                    planned_top1_date
                    .strftime(
                        "%Y-%m-%d"
                    )
                )

        # ==================================================
        # TOP DRESSING 2 DATE
        # ==================================================
        #
        # IMPORTANT AGRONOMIC RULE:
        #
        # If actual Top Dressing 1 exists:
        #
        #     Top 2 = Actual Top 1 + 28 days
        #
        # Otherwise:
        #
        #     Top 2 = Planned Top 1 + 28 days
        #
        # This is a ROLLING fertilizer schedule.
        #
        # ==================================================

        if top2_index is not None:

            top2_record = records[
                top2_index
            ]

            planned_top2_date = None

            # ------------------------------------------------
            # ACTUAL TOP 1 EXISTS
            # ------------------------------------------------

            if actual_top_1_date is not None:

                planned_top2_date = (
                    pd.to_datetime(
                        actual_top_1_date
                    )
                    +
                    pd.Timedelta(
                        days=28
                    )
                )

            # ------------------------------------------------
            # NO ACTUAL TOP 1
            # ------------------------------------------------

            elif top1_index is not None:

                top1_planned_date = pd.to_datetime(
                    records[
                        top1_index
                    ].get(
                        "Planned Date"
                    ),
                    errors="coerce"
                )

                if pd.notna(
                    top1_planned_date
                ):

                    planned_top2_date = (
                        top1_planned_date
                        +
                        pd.Timedelta(
                            days=28
                        )
                    )

            # ------------------------------------------------
            # APPLY TOP 2 DATE
            # ------------------------------------------------

            if planned_top2_date is not None:

                top2_record[
                    "Planned Date"
                ] = (
                    planned_top2_date
                    .strftime(
                        "%Y-%m-%d"
                    )
                )

        # ==================================================
        # END FIELD + FERTILIZER PROCESSING
        # ==================================================

    # ======================================================
    # FINAL WHOLE-BAG NORMALISATION
    # ======================================================

    for record in records:

        planned = whole_bags(
            record.get(
                "Planned Quantity (bags)",
                0
            )
        )

        actual = whole_bags(
            record.get(
                "Actual Quantity (bags)",
                0
            )
        )

        balance = whole_bags(
            max(
                planned - actual,
                0
            )
        )

        record[
            "Planned Quantity (bags)"
        ] = planned

        record[
            "Actual Quantity (bags)"
        ] = actual

        record[
            "Balance (bags)"
        ] = balance

        if balance <= 0:

            record[
                "Balance Display"
            ] = "Complete"

        else:

            record[
                "Balance Display"
            ] = (
                f"{balance} bags remaining"
            )

    return records

# ==========================================================
# AUTOMATIC FERTILIZER PROGRAMME
# ==========================================================

@activity_bp.route(
    "/agriculture/generate-fertilizer-programme"
)
def generate_fertilizer_programme_route():

    if "username" not in session:

        return redirect(
            url_for("login")
        )

    from modules.season import (
        get_active_season
    )

    season = get_active_season()

    try:

        result = generate_fertilizer_programme(
            season=season
        )

        if result.empty:

            flash(
                "No fertilizer programme could be generated.",
                "warning"
            )

        else:

            flash(
                f"Fertilizer programme generated successfully "
                f"for season {season}. "
                f"{result['Field'].nunique()} fields processed.",
                "success"
            )

    except Exception as e:

        print(
            "FERTILIZER PROGRAMME ERROR:",
            e
        )

        flash(
            f"Error generating fertilizer programme: {e}",
            "danger"
        )

    return redirect(
        url_for(
            "activities.fertilizer_schedule"
        )
    )

@activity_bp.route('/agriculture/harvesting')
def harvesting_home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('agriculture/harvesting_home.html')

HARVEST_FILE = "data/harvesting_records.xlsx"

@activity_bp.route("/agriculture/cane-cutting", methods=["GET", "POST"])
def cane_cutting():
    if "username" not in session:
        return redirect(url_for("login"))
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == "POST":
        try:
            # Existing fields
            date = request.form["date"]
            field = request.form["field"]
            crop_type = request.form["crop_type"]
            area = float(request.form["harvested_area"])
            bundles = int(request.form["bundles"])
            yield_tons = float(request.form["yield_tons"])  # already calculated in frontend

            # NEW labor fields (with Fire Team instead of Tools Keeper)
            foreman = int(request.form.get("foreman", 0))
            capitaos = int(request.form.get("capitaos", 0))
            water_drawers = int(request.form.get("water_drawers", 0))
            dippers = int(request.form.get("dippers", 0))
            needlemen = int(request.form.get("needlemen", 0))
            bicycle_guards = int(request.form.get("bicycle_guards", 0))
            feeder_breakers = int(request.form.get("feeder_breakers", 0))
            cane_cutters = int(request.form.get("cane_cutters", 0))
            first_aider = int(request.form.get("first_aider", 0))
            she_rep = int(request.form.get("she_rep", 0))
            fire_team = int(request.form.get("fire_team", 0))

            # Auto-calculate Mandays (sum of all labor counts)
            mandays = (
                foreman + capitaos + water_drawers + dippers +
                needlemen + bicycle_guards + feeder_breakers +
                cane_cutters + first_aider + she_rep + fire_team
            )

            # Combine all fields
            new_data = {
                "Date": date,
                "Field": field,
                "Crop Type": crop_type,
                "Harvested Area (ha)": area,
                "Bundles": bundles,
                "Yield (Tons)": yield_tons,
                "Mandays": mandays,
                "Foreman": foreman,
                "Capitaos": capitaos,
                "Water Drawers": water_drawers,
                "Dippers": dippers,
                "Needlemen": needlemen,
                "Bicycle Guards": bicycle_guards,
                "Feeder Breakers": feeder_breakers,
                "Cane Cutters": cane_cutters,
                "First-Aider": first_aider,
                "SHE Representative": she_rep,
                "Fire Team": fire_team,
                "Season": season
            }

            # Append to Excel
            if os.path.exists(HARVEST_FILE):
                df = pd.read_excel(HARVEST_FILE)
            else:
                df = pd.DataFrame(columns=new_data.keys())

            # Ensure all new columns exist if older file had fewer columns
            for col in new_data.keys():
                if col not in df.columns:
                    df[col] = None

            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_excel(HARVEST_FILE, index=False)

            flash("Cane cutting record saved successfully!", "success")
            return redirect(url_for("activities.cane_cutting"))

        except Exception as e:
            flash(f"Error saving record: {e}", "danger")
            return redirect(url_for("activities.cane_cutting"))

    return render_template("agriculture/cane_cutting.html", season=season)


@activity_bp.route("/agriculture/cane-cutting-report")
def cane_cutting_report():
    try:
        from modules.season import get_active_season
        current_season = get_active_season()
        selected_crop = request.args.get("crop_type", "")
        df = pd.read_excel(HARVEST_FILE)

        if "Season" in df.columns:
            df = df[df["Season"] == current_season]

        # Apply crop filter
        crop_types = sorted(df["Crop Type"].dropna().unique())
        if selected_crop:
            df = df[df["Crop Type"] == selected_crop]

        chart_data = {
            "Field": df["Field"].tolist(),
            "Yield": df["Yield (Tons)"].tolist(),
            "Area": df["Harvested Area (ha)"].tolist()
        }

        return render_template("agriculture/cane_cutting_report.html",
                               records=df.to_dict(orient="records"),
                               season=current_season,
                               crop_types=crop_types,
                               selected_crop=selected_crop,
                               chart_data=chart_data)
    except Exception as e:
        flash(f"Error loading cane cutting report: {e}", "danger")
        return render_template("agriculture/cane_cutting_report.html",
                               records=[], season="Unknown", crop_types=[], selected_crop="", chart_data=None)


HAULAGE_FILE = "data/yield_data.xlsx"

@activity_bp.route("/agriculture/haulage", methods=["GET", "POST"])
def haulage():
    from modules.season import get_active_season
    season = get_active_season()
    if request.method == "POST":
        data = {
            "Date": request.form.get("Date"),
            "Field": request.form.get("Field"),
            "Crop": request.form.get("Crop"),
            "Bundles": request.form.get("Bundles"),
            "Yield (Tons)": request.form.get("Yield (Tons)"),
            "Vehicle": request.form.get("Vehicle"),
            "Remarks": request.form.get("Remarks"),
            "Season": request.form.get("Season")
        }

        try:
            if os.path.exists(HAULAGE_FILE):
                df = pd.read_excel(HAULAGE_FILE)
            else:
                df = pd.DataFrame(columns=data.keys())

            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(HAULAGE_FILE, index=False)
            flash("Haulage entry saved successfully!", "success")
        except Exception as e:
            flash(f"Failed to save record: {e}", "danger")

        return redirect(url_for("activities.haulage"))

    return render_template("agriculture/haulage.html", season=season)


from flask import render_template, request
import pandas as pd
import os

@activity_bp.route('/haulage_report')
def haulage_report():
    excel_path = 'data/yield_data.xlsx'
    active_season_file = 'data/active_season.txt'

    if not os.path.exists(excel_path):
        return "Haulage data file not found.", 404

    # Read Excel file
    df = pd.read_excel(excel_path)

    # Ensure required columns exist
    expected_columns = ['Date', 'Field', 'Crop', 'Bundles', 'Yield (Tons)', 'Vehicle', 'Remarks', 'Season']
    if not all(col in df.columns for col in expected_columns):
        return "Missing required columns in the Excel file.", 500

    # Convert Date column to datetime (ISO 'YYYY-MM-DD' is default)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()

    df = df.dropna(subset=['Date'])

    # Load active season
    active_season = None
    if os.path.exists(active_season_file):
        with open(active_season_file, 'r') as f:
            active_season = f.read().strip()

    # Initial filter by season
    filtered_df = df[df['Season'] == active_season] if active_season else df
    print(f"Initial filtered rows for season '{active_season}': {len(filtered_df)}")

    # Get filters from GET parameters
    selected_field = request.args.get('field', '')
    selected_crop = request.args.get('crop', '')
    selected_vehicle = request.args.get('vehicle', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Apply filters
    if selected_field:
        filtered_df = filtered_df[filtered_df['Field'] == selected_field]
    if selected_crop:
        filtered_df = filtered_df[filtered_df['Crop'] == selected_crop]
    if selected_vehicle:
        filtered_df = filtered_df[filtered_df['Vehicle'] == selected_vehicle]
    if start_date:
        try:
            start = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['Date'] >= start]
        except Exception as e:
            print(f"Start date error: {e}")
    if end_date:
        try:
            end = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df['Date'] <= end]
        except Exception as e:
            print(f"End date error: {e}")

    print(f"Final filtered rows: {len(filtered_df)}")

    # Dropdown filter options
    fields = sorted(df['Field'].dropna().unique())
    crops = sorted(df['Crop'].dropna().unique())
    vehicles = sorted(df['Vehicle'].dropna().unique())

    # Chart and totals
    if not filtered_df.empty:
        grouped = filtered_df.groupby('Field')['Yield (Tons)'].sum().reset_index()
        chart_data = {
            'labels': grouped['Field'].tolist(),
            'values': grouped['Yield (Tons)'].tolist()
        }
        total_bundles = int(filtered_df['Bundles'].sum())
        total_yield = float(filtered_df['Yield (Tons)'].sum())
    else:
        chart_data = {'labels': [], 'values': []}
        total_bundles = 0
        total_yield = 0

    return render_template(
        'agriculture/haulage_report.html',
        haulage_data=filtered_df.to_dict(orient='records'),
        chart_data=chart_data,
        fields=fields,
        crops=crops,
        vehicles=vehicles,
        selected_field=selected_field,
        selected_crop=selected_crop,
        selected_vehicle=selected_vehicle,
        start_date=start_date,
        end_date=end_date,
        season=active_season,
        total_bundles=total_bundles,
        total_yield=total_yield
    )

@activity_bp.route('/haulage/edit', methods=['GET', 'POST'])
def edit_haulage():

    field = request.args.get('field')
    crop = request.args.get('crop')
    vehicle = request.args.get('vehicle')

    df = pd.read_excel('data/yield_data.xlsx')

    match = (df['Field'] == field) & \
            (df['Crop'] == crop) & \
            (df['Vehicle'] == vehicle)

    if not df[match].empty:
        row_index = df[match].index[0]
        if request.method == 'POST':
            df.at[row_index, 'Date'] = request.form['Date']
            df.at[row_index, 'Field'] = request.form['Field']
            df.at[row_index, 'Crop'] = request.form['Crop']
            df.at[row_index, 'Bundles'] = int(request.form['Bundles'])
            df.at[row_index, 'Yield (Tons)'] = float(request.form['Yield (Tons)'])
            df.at[row_index, 'Vehicle'] = request.form['Vehicle']
            df.at[row_index, 'Remarks'] = request.form['Remarks']
            df.at[row_index, 'Season'] = request.form['Season']
            df.to_excel('data/yield_data.xlsx', index=False)
            flash('Haulage record updated successfully.', 'success')
            return redirect(url_for('activities.haulage_report'))

        row = df.loc[row_index].to_dict()
        return render_template('agriculture/edit_haulage.html', row=row)
    else:
        flash("Record not found.", "danger")
        return redirect(url_for('activities.haulage_report'))

@activity_bp.route('/haulage/delete')
def delete_haulage():

    field = request.args.get('field')
    crop = request.args.get('crop')
    vehicle = request.args.get('vehicle')

    df = pd.read_excel('data/yield_data.xlsx')

    match = (df['Field'] == field) & \
            (df['Crop'] == crop) & \
            (df['Vehicle'] == vehicle)

    if not df[match].empty:
        df = df[~match]
        df.to_excel('data/yield_data.xlsx', index=False)
        flash('Haulage record deleted successfully.', 'success')
    else:
        flash('Record not found.', 'danger')

    return redirect(url_for('activities.haulage_report'))


ERS_REPORT_FOLDER = "ERS_reports"


# ======================================================
# ERS ENTRY (SEASONAL)
# ======================================================
@activity_bp.route('/agriculture/ers-entry', methods=['GET', 'POST'])
def ers_entry():
    if 'username' not in session:
        return redirect(url_for('login'))

    from modules.season import get_active_season
    season = get_active_season()
    safe_season = season.replace("/", "-")

    selected_field = request.args.get("main_field") or request.form.get("main_field")
    main_fields, subfields, report_data = [], [], []
    ers_inputs = {}

    try:
        # ---------------------------------------------
        # Load data
        # ---------------------------------------------
        df_fields = pd.read_excel("data/registered_fields.xlsx")
        df_yield = pd.read_excel("data/yield_data.xlsx")

        # FILTER STRICTLY BY SEASON
        df_fields = df_fields[df_fields["Season"] == season]
        df_yield = df_yield[df_yield["Season"] == season]

        main_fields = sorted(df_fields["Main Field"].dropna().unique())

        if selected_field:
            subfields = df_fields[
                df_fields["Main Field"] == selected_field
            ]["Field"].dropna().unique().tolist()

        action = request.form.get("action", "report")

        # ---------------------------------------------
        # GENERATE REPORT
        # ---------------------------------------------
        if request.method == "POST" and selected_field and subfields:

            if action != "save":

                ers_inputs = {}
                for key in request.form:
                    if key.startswith('ers_values[') and key.endswith(']'):
                        field_name = key[len('ers_values['):-1]
                        ers_inputs[field_name] = request.form[key]

                totals = {
                    "Hectares": 0,
                    "Bundles": 0,
                    "Yield": 0,
                    "Tons Sugar": 0
                }

                total_weighted_ers = 0
                total_tons = 0

                for field in subfields:

                    field_row = df_fields[df_fields["Field"] == field]
                    yield_row = df_yield[df_yield["Field"] == field]

                    if field_row.empty:
                        continue

                    grower = field_row.iloc[0]["Growers Name"]
                    hectares = field_row.iloc[0]["Hectares"]

                    bundles = yield_row["Bundles"].sum()
                    tons_cane = yield_row["Yield (Tons)"].sum()

                    ers_raw = ers_inputs.get(field, 0)
                    try:
                        ers_val = float(ers_raw)
                    except ValueError:
                        ers_val = 0

                    tons_sugar = tons_cane * ers_val / 100
                    avg_weight = tons_cane / bundles if bundles else 0
                    tch = tons_cane / hectares if hectares else 0
                    tsh = tons_sugar / hectares if hectares else 0

                    totals["Hectares"] += hectares
                    totals["Bundles"] += bundles
                    totals["Yield"] += tons_cane
                    totals["Tons Sugar"] += tons_sugar

                    total_weighted_ers += tons_cane * ers_val
                    total_tons += tons_cane

                    report_data.append({
                        "Grower": grower,
                        "Field": field,
                        "Hectares": f"{hectares:,.3f}",
                        "Bundles": f"{bundles:,.2f}",
                        "Yield": f"{tons_cane:,.2f}",
                        "AvgWeight": f"{avg_weight:,.2f}",
                        "TCH": f"{tch:,.2f}",
                        "ERS": f"{ers_val:,.2f}",
                        "TonsSugar": f"{tons_sugar:,.2f}",
                        "TSH": f"{tsh:,.2f}"
                    })

                # ---------------------------------------------
                # SEASONAL TOTALS
                # ---------------------------------------------
                seasonal_ers = total_weighted_ers / total_tons if total_tons else 0
                avg_weight = totals["Yield"] / totals["Bundles"] if totals["Bundles"] else 0
                avg_tch = totals["Yield"] / totals["Hectares"] if totals["Hectares"] else 0
                avg_tsh = totals["Tons Sugar"] / totals["Hectares"] if totals["Hectares"] else 0

                report_data.append({
                    "Grower": "TOTAL",
                    "Field": "",
                    "Hectares": f"{totals['Hectares']:,.3f}",
                    "Bundles": f"{totals['Bundles']:,.2f}",
                    "Yield": f"{totals['Yield']:,.2f}",
                    "AvgWeight": f"{avg_weight:,.2f}",
                    "TCH": f"{avg_tch:,.2f}",
                    "ERS": f"{seasonal_ers:,.2f}",
                    "TonsSugar": f"{totals['Tons Sugar']:,.2f}",
                    "TSH": f"{avg_tsh:,.2f}"
                })

                session["ers_report_data"] = report_data
                session["ers_inputs"] = ers_inputs

            # ---------------------------------------------
            # SAVE REPORT (SEASON SAFE)
            # ---------------------------------------------
            else:
                report_data = session.get("ers_report_data", [])
                ers_inputs = session.get("ers_inputs", {})

                if report_data:
                    os.makedirs(ERS_REPORT_FOLDER, exist_ok=True)
                    file_name = f"{selected_field}_ERS_{safe_season}.json"

                    with open(os.path.join(ERS_REPORT_FOLDER, file_name), "w") as f:
                        json.dump({
                            "season": season,
                            "main_field": selected_field,
                            "ers_values": ers_inputs,
                            "report": report_data
                        }, f, indent=2)

                    flash(f"ERS report saved for season {season}", "success")
                else:
                    flash("No ERS data to save.", "warning")

    except Exception as e:
        flash(f"Error generating ERS% report: {e}", "danger")

    return render_template(
        "agriculture/ers_entry.html",
        season=season,
        selected_field=selected_field,
        main_fields=main_fields,
        subfields=subfields,
        ers_inputs=ers_inputs,
        report_data=report_data,
        logo_path="logo.png"
    )


# ======================================================
# ERS REPORT VIEWER (SEASONAL)
# ======================================================
@activity_bp.route('/agriculture/ers-report')
def ers_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    from modules.season import get_active_season
    season = get_active_season()              # ✅ season defined here
    safe_season = season.replace("/", "-")    # ✅ now this is valid

    reports_dir = ERS_REPORT_FOLDER
    selected_file = request.args.get('report')
    reports = []
    report_data = []

    desired_keys = [
        "Grower", "Field", "Hectares", "Bundles",
        "Yield", "AvgWeight", "TCH", "ERS",
        "TonsSugar", "TSH"
    ]

    try:
        os.makedirs(reports_dir, exist_ok=True)

        reports = [
            f for f in os.listdir(reports_dir)
            if f.endswith(f"_{safe_season}.json")
        ]

        if selected_file:
            file_path = os.path.join(reports_dir, selected_file)
            with open(file_path, "r") as f:
                data = json.load(f)
                for row in data.get("report", []):
                    report_data.append({k: row.get(k, "") for k in desired_keys})
        else:
            report_data = None

    except Exception as e:
        flash(f"Error loading ERS reports: {e}", "danger")
        report_data = None

    return render_template(
        "agriculture/ers_report_viewer.html",
        reports=reports,
        selected_file=selected_file,
        report_data=report_data,
        season=season
    )


@activity_bp.route('/tractor-report', methods=['GET'])
def tractor_operations_report():
    excel_path = 'data/tractor_operations.xlsx'

    # Load data safely
    if not os.path.exists(excel_path):
        return render_template(
            'agriculture/tractor_operations_report.html',
            records=[], total_hours=0, total_fuel=0,
            chart_data=[], fuel_chart_data=[],
            most_frequent_activity="N/A", average_fuel_per_ha=0,
            average_hours_per_day=0, grouped_by_tractor=[]
        )

    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()

    # Convert date column to datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
    else:
        df['Date'] = pd.NaT

    # Filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tractor_filter = request.args.get('tractor')

    if start_date:
        df = df[df['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['Date'] <= pd.to_datetime(end_date)]
    if tractor_filter and 'Tractor Number' in df.columns:
        df = df[df['Tractor Number'].str.contains(tractor_filter, case=False, na=False)]

    # Fill missing numeric data
    for col in ['Fuel Used', 'Area (ha)', 'Hours Worked', 'Hour Meter Open', 'Hour Meter Closed']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    # Recalculate derived columns
    df['Hours Worked'] = df['Hour Meter Closed'] - df['Hour Meter Open']
    df['Fuel per ha'] = df.apply(lambda row: round(row['Fuel Used'] / row['Area (ha)'], 2) if row['Area (ha)'] else 0, axis=1)
    df['Hours per ha'] = df.apply(lambda row: round(row['Hours Worked'] / row['Area (ha)'], 2) if row['Area (ha)'] else 0, axis=1)

    # Totals
    total_hours = round(df['Hours Worked'].sum(), 2)
    total_fuel = round(df['Fuel Used'].sum(), 2)

    # Chart data
    chart_data = df.groupby('Activity').agg({'Hours Worked': 'sum', 'Area (ha)': 'sum'}).reset_index().to_dict(orient='records')
    fuel_chart_data = df.groupby('Tractor Number').agg({'Fuel Used': 'sum'}).reset_index().sort_values(by='Fuel Used', ascending=False).to_dict(orient='records')

    # Summary insights
    most_frequent_activity = df['Activity'].value_counts().idxmax() if not df.empty else "N/A"
    avg_fuel_per_ha = (df['Fuel Used'].sum() / df['Area (ha)'].sum()) if df['Area (ha)'].sum() > 0 else 0
    avg_hours_per_day = df.groupby(df['Date'].dt.date)['Hours Worked'].sum().mean() if not df.empty else 0

    # Tractor-wise breakdown
    if 'Tractor Number' in df.columns:
        grouped_by_tractor = df.groupby('Tractor Number').agg({
            'Hours Worked': 'sum',
            'Fuel Used': 'sum',
            'Area (ha)': 'sum'
        }).reset_index().sort_values(by='Hours Worked', ascending=False).to_dict(orient='records')
    else:
        grouped_by_tractor = []

    return render_template(
        'agriculture/tractor_operations_report.html',
        records=df.to_dict(orient='records'),
        total_hours=total_hours,
        total_fuel=total_fuel,
        chart_data=chart_data,
        fuel_chart_data=fuel_chart_data,
        most_frequent_activity=most_frequent_activity,
        average_fuel_per_ha=round(avg_fuel_per_ha, 2),
        average_hours_per_day=round(avg_hours_per_day, 2),
        grouped_by_tractor=grouped_by_tractor
    )


@activity_bp.route('/equipment/manage')
def equipment_manage():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('equipment/manage.html')


EQUIPMENT_FILE = "data/equipment_records.xlsx"

@activity_bp.route('/equipment/add', methods=['GET', 'POST'])
def add_equipment():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            data = {
                "Equipment ID": request.form["equipment_id"],
                "Name": request.form["name"],
                "Category": request.form["category"],
                "Purchase Date": request.form["purchase_date"],
                "Status": request.form["status"],
                "Operator": request.form["operator"],
                "Remarks": request.form["remarks"]
            }

            if os.path.exists(EQUIPMENT_FILE):
                df = pd.read_excel(EQUIPMENT_FILE)
            else:
                df = pd.DataFrame(columns=data.keys())

            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(EQUIPMENT_FILE, index=False)

            flash("Equipment entry saved successfully!", "success")
            return redirect(url_for('activities.add_equipment'))

        except Exception as e:
            flash(f"Error saving equipment entry: {e}", "danger")

    return render_template('equipment/add_equipment.html')


@activity_bp.route("/equipment/list", methods=["GET", "POST"])
def equipment_list():
    if not os.path.exists(EQUIPMENT_FILE):
        df = pd.DataFrame(columns=["Equipment ID", "Name", "Category", "Purchase Date", "Status", "Operator", "Remarks"])
        df.to_excel(EQUIPMENT_FILE, index=False)

    df = pd.read_excel(EQUIPMENT_FILE)

    if request.method == "POST":
        try:
            update_index = int(request.form.get("update"))
            # Update only the targeted row
            df.at[update_index, "Name"] = request.form.get(f"name_{update_index}")
            df.at[update_index, "Category"] = request.form.get(f"category_{update_index}")
            df.at[update_index, "Purchase Date"] = request.form.get(f"purchase_date_{update_index}")
            df.at[update_index, "Status"] = request.form.get(f"status_{update_index}")
            df.at[update_index, "Operator"] = request.form.get(f"operator_{update_index}")
            df.at[update_index, "Remarks"] = request.form.get(f"remarks_{update_index}")

            df.to_excel(EQUIPMENT_FILE, index=False)
            flash("Equipment updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating equipment: {e}", "danger")

        return redirect(url_for("activities.equipment_list"))

    equipment_list = df.to_dict(orient="records")
    return render_template("equipment/equipment_list.html", equipment_list=equipment_list)

MAINTENANCE_FILE = "data/equipment_maintenance.xlsx"

@activity_bp.route("/equipment/add-maintenance", methods=["GET", "POST"])
def add_equipment_maintenance():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            data = {
                "Equipment ID": request.form["equipment_id"],
                "Date": request.form["date"],
                "Description": request.form["description"],
                "Cost": float(request.form["cost"]) if request.form["cost"] else 0,
                "Performed By": request.form["performed_by"],
                "Status": request.form["status"],
                "Remarks": request.form["remarks"]
            }

            df = pd.read_excel(MAINTENANCE_FILE) if os.path.exists(MAINTENANCE_FILE) else pd.DataFrame()
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(MAINTENANCE_FILE, index=False)

            flash("Maintenance record saved successfully!", "success")
            return redirect(url_for("activities.add_equipment_maintenance"))

        except Exception as e:
            flash(f"Error saving maintenance record: {e}", "danger")
            return redirect(url_for("activities.add_equipment_maintenance"))

    return render_template("equipment/add_maintenance.html")


@activity_bp.route("/equipment/maintenance-report")
def maintenance_report():
    try:
        df = pd.read_excel(MAINTENANCE_FILE) if os.path.exists(MAINTENANCE_FILE) else pd.DataFrame()

        # Clean column names
        df.columns = df.columns.str.strip()

        # Filters
        equipment_id = request.args.get("equipment_id", "").strip()
        status = request.args.get("status", "").strip()

        # Normalize data types for comparison
        if not df.empty:
            if "Equipment ID" in df.columns:
                df["Equipment ID"] = df["Equipment ID"].astype(str).str.strip()
            if "Status" in df.columns:
                df["Status"] = df["Status"].astype(str).str.strip()

        if equipment_id:
            df = df[df["Equipment ID"] == equipment_id]
        if status:
            df = df[df["Status"] == status]

        equipment_ids = df["Equipment ID"].dropna().unique() if "Equipment ID" in df.columns else []
        statuses = df["Status"].dropna().unique() if "Status" in df.columns else []

        return render_template("equipment/equipment_maintenance_report.html",
                               records=df.to_dict(orient="records"),
                               equipment_ids=equipment_ids,
                               statuses=statuses,
                               selected_equipment=equipment_id,
                               selected_status=status)
    except Exception as e:
        flash(f"Error loading maintenance report: {e}", "danger")
        return render_template("equipment/equipment_maintenance_report.html",
                               records=[],
                               equipment_ids=[],
                               statuses=[],
                               selected_equipment="",
                               selected_status="")


import pandas as pd
from flask import request, redirect, url_for, render_template, flash
import os

@activity_bp.route('/upload_harvest_program', methods=['GET', 'POST'])
def upload_harvest_program():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            season_path = 'data/active_season.txt'
            with open(season_path, 'r') as f:
                season = f.read().strip()

            safe_season = season.replace('/', '_')  # 🔐 sanitize season
            filename = f"harvest_program_{safe_season}.xlsx"
            os.makedirs('data', exist_ok=True)
            save_path = os.path.join('data', filename)

            file.save(save_path)
            flash(f'Harvest program for {season} uploaded successfully.', 'success')
            return redirect(url_for('activities.view_harvest_program'))
        else:
            flash('Please upload a valid Excel file (.xlsx)', 'danger')

    return render_template('harvesting/upload_harvest_program.html')

@activity_bp.route('/view_harvest_program')
def view_harvest_program():
    try:
        season_path = 'data/active_season.txt'
        with open(season_path, 'r') as f:
            season = f.read().strip()

        safe_season = season.replace('/', '_')
        filename = f"harvest_program_{safe_season}.xlsx"
        file_path = os.path.join('data', filename)

        sheet_name = f"HARV.{season.split('/')[0]}"
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # 🔢 Round float columns to 2 decimals
        df = df.apply(lambda x: x.round(2) if x.dtype == 'float' else x)

        table_data = df.to_dict(orient='records')
        columns = df.columns.tolist()
    except Exception as e:
        flash(f'Error loading harvesting program: {e}', 'danger')
        table_data = []
        columns = []

    return render_template("harvesting/view_harvest_program.html",
                           columns=columns,
                           table_data=table_data,
                           season=season)

@activity_bp.route('/harvest_program_dashboard')
def harvest_program_dashboard():
    try:
        season_path = 'data/active_season.txt'
        with open(season_path, 'r') as f:
            season = f.read().strip()
    except Exception as e:
        season = "N/A"
        flash(f'⚠️ Could not determine active season: {e}', 'warning')

    return render_template('harvesting/dashboard.html', season=season)


from flask import send_file

@activity_bp.route('/download_harvest_program')
def download_harvest_program():
    try:
        season_path = 'data/active_season.txt'
        with open(season_path, 'r') as f:
            season = f.read().strip()

        safe_season = season.replace('/', '_')
        filename = f"harvest_program_{safe_season}.xlsx"
        file_path = os.path.join('data', filename)

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'⚠️ Could not download file: {e}', 'warning')
        return redirect(url_for('activities.harvest_program_dashboard'))


@activity_bp.route('/change_season', methods=['GET', 'POST'])
def change_season():
    season_path = 'data/active_season.txt'

    if request.method == 'POST':
        new_season = request.form['season'].strip()
        if new_season:
            with open(season_path, 'w') as f:
                f.write(new_season)
            flash(f'✅ Season changed to {new_season}', 'success')
            return redirect(url_for('activities.harvest_program_dashboard'))
        else:
            flash('❌ Please enter a valid season.', 'danger')

    # Load current season for the form
    try:
        with open(season_path, 'r') as f:
            current_season = f.read().strip()
    except:
        current_season = ''

    return render_template('harvesting/change_season.html', current_season=current_season)



@activity_bp.route('/upload-file-to-drive', methods=['POST'])
def upload_file_to_drive():
    filename = request.form.get('filename')  # e.g., 'harvest_program.xlsx'
    if not filename:
        return "Missing filename", 400

    local_path = os.path.join('data', filename)
    if not os.path.exists(local_path):
        return f"{filename} not found in /data", 404

    try:
        file_id = upload_excel_to_drive(local_path, filename)
        return jsonify({"status": "success", "drive_file_id": file_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


import requests

@activity_bp.route('/harvest_program_analytics')
def harvest_program_analytics():
    import pandas as pd
    import json

    try:
        # Load season and file
        season_path = 'data/active_season.txt'
        with open(season_path, 'r') as f:
            season = f.read().strip()
        safe_season = season.replace('/', '_')
        file_path = os.path.join('data', f'harvest_program_{safe_season}.xlsx')

        # Load and clean data
        sheet_name = f"HARV.{season.split('/')[0]}"
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df.columns = df.columns.str.strip().str.upper()  # Normalize all column names
        df = df.dropna(subset=['FIELD', 'VARIETY'])

        # Format date column
        df['Date'] = pd.to_datetime(df['DATE'], errors='coerce')
        df = df.dropna(subset=['Date'])

        # Grouped data
        est_tch_by_field = df.groupby('FIELD')['EST. TCH'].mean().round(2).to_dict()
        est_vs_actual = (
            df[['FIELD', 'EST. TCH', 'ACTUAL TCH']]
            .dropna()
            .astype({'FIELD': str})
            .to_dict(orient='records')
        )
        flash(f"Chart Data Sample: {est_vs_actual[:3]}", "info")

        area_by_variety = df.groupby('VARIETY')['AREA (HA)'].sum().round(2).to_dict()

        # Cumulative area over time
        df_sorted = df.sort_values('DATE')
        df_sorted['Cumulative Area'] = df_sorted['AREA (HA)'].cumsum().round(2)
        df_sorted['Date'] = df_sorted['Date'].dt.strftime('%Y-%m-%d')  # convert to string
        area_over_time = df_sorted[['Date', 'Cumulative Area']].dropna().to_dict(orient='records')

        return render_template(
            'harvesting/analytics.html',
            season=season,
            est_tch_by_field=json.dumps(est_tch_by_field),
            est_vs_actual=json.dumps(est_vs_actual),
            area_by_variety=json.dumps(area_by_variety),
            area_over_time=json.dumps(area_over_time)
        )
    except Exception as e:
        flash(f'⚠️ Could not load analytics: {e}', 'danger')
        return redirect(url_for('activities.harvest_program_dashboard'))

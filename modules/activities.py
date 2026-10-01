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

@activity_bp.route("/agriculture/herbicide", methods=["GET", "POST"])
def herbicide():
    if 'username' not in session:
        return redirect(url_for('login'))

    fields = ["Date", "Field", "Crop Type", "Applied Area (ha)", "MSMA", "MCPA", "Ametryn", "Altrazine", "Servian WP",
              "Round-Up", "Dual Magnum", "Sprint", "Garlon", "Acetochlor", "Metolachlor", "BB5", "Mandays", "Season"]

    if request.method == "POST":
        try:
            data = {field: request.form.get(field, "") for field in fields}
            data["Season"] = get_active_season()

            df = pd.read_excel(HERBICIDE_FILE) if os.path.exists(HERBICIDE_FILE) else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(HERBICIDE_FILE, index=False)

            flash("Herbicide application saved successfully!", "success")
            return redirect(url_for("activities.herbicide"))
        except Exception as e:
            flash(f"Error: {e}", "danger")

    return render_template("agriculture/herbicide.html", season=get_active_season())

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
    Return the fertilizer programme summary for a season.

    This is the SINGLE source of truth for:
        - Fertilizer Schedule page
        - Main Dashboard

    Applied applications are identified using Actual Date.
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

    if not os.path.exists(FERTILIZER_SCHEDULE_FILE):
        return summary

    try:

        df = pd.read_excel(
            FERTILIZER_SCHEDULE_FILE
        )

        if df.empty:
            return summary

        # --------------------------------------------------
        # CLEAN COLUMN NAMES
        # --------------------------------------------------

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        # --------------------------------------------------
        # SEASON
        # --------------------------------------------------

        if "Season" not in df.columns:
            return summary

        df["Season"] = (
            df["Season"]
            .astype(str)
            .str.strip()
        )

        df = df[
            df["Season"] == str(season).strip()
        ].copy()

        if df.empty:
            return summary

        summary["programme_exists"] = True

        # --------------------------------------------------
        # PLANNED DATE
        # --------------------------------------------------

        if "Planned Date" not in df.columns:
            return summary

        df["Planned Date"] = pd.to_datetime(
            df["Planned Date"],
            errors="coerce"
        )

        # --------------------------------------------------
        # ACTUAL DATE
        # --------------------------------------------------

        if "Actual Date" in df.columns:

            df["Actual Date"] = pd.to_datetime(
                df["Actual Date"],
                errors="coerce"
            )

        else:

            df["Actual Date"] = pd.NaT

        # --------------------------------------------------
        # REMOVE INVALID PLANNED DATES
        # --------------------------------------------------

        df = df.dropna(
            subset=["Planned Date"]
        )

        if df.empty:
            return summary

        # --------------------------------------------------
        # TODAY
        # --------------------------------------------------

        today = pd.Timestamp.today().normalize()

        seven_days = (
            today +
            pd.Timedelta(days=7)
        )

        # --------------------------------------------------
        # APPLIED
        # --------------------------------------------------

        applied_mask = (
            df["Actual Date"].notna()
        )

        summary["applied"] = int(
            applied_mask.sum()
        )

        # --------------------------------------------------
        # OUTSTANDING
        # --------------------------------------------------

        outstanding = df[
            ~applied_mask
        ].copy()

        summary["total"] = int(
            len(outstanding)
        )

        # --------------------------------------------------
        # OVERDUE
        # --------------------------------------------------

        summary["overdue"] = int(
            (
                outstanding["Planned Date"] < today
            ).sum()
        )

        # --------------------------------------------------
        # DUE TODAY
        # --------------------------------------------------

        summary["due_today"] = int(
            (
                outstanding["Planned Date"] == today
            ).sum()
        )

        # --------------------------------------------------
        # DUE WITHIN 7 DAYS
        # --------------------------------------------------

        summary["due_soon"] = int(
            (
                (outstanding["Planned Date"] > today) &
                (outstanding["Planned Date"] <= seven_days)
            ).sum()
        )

        # --------------------------------------------------
        # SCHEDULED
        # --------------------------------------------------

        summary["scheduled"] = int(
            (
                outstanding["Planned Date"] > seven_days
            ).sum()
        )

        return summary

    except Exception as e:

        print(
            "FERTILIZER SCHEDULE SUMMARY ERROR:",
            e
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

    from modules.season import (
        get_active_season
    )

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

        if os.path.exists(
            FERTILIZER_SCHEDULE_FILE
        ):

            df = pd.read_excel(
                FERTILIZER_SCHEDULE_FILE
            )

        else:

            df = pd.DataFrame()

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
    # LOAD FERTILIZER PROGRAMME
    # ======================================================

    reminders = []

    if not os.path.exists(
        FERTILIZER_SCHEDULE_FILE
    ):

        reminder_summary = {

            "overdue": 0,
            "today": 0,
            "due_soon": 0,
            "scheduled": 0,
            "partial": 0,
            "applied": 0
        }

        return render_template(
            "agriculture/fertilizer_schedule.html",
            season=season,
            reminders=reminders,
            reminder_summary=reminder_summary
        )

    schedule_df = pd.read_excel(
        FERTILIZER_SCHEDULE_FILE
    )

    # ======================================================
    # SEASON FILTER
    # ======================================================

    if "Season" in schedule_df.columns:

        schedule_df = schedule_df[
            schedule_df["Season"]
            .astype(str)
            .str.strip()
            ==
            str(season).strip()
        ].copy()

    # ======================================================
    # REMOVE DUPLICATE PROGRAMME ROWS
    # ======================================================
    #
    # This is critical.
    #
    # Old programme rows can remain in
    # fertilizer_schedule.xlsx after the programme has
    # been regenerated.
    #
    # Only one Field + Operation + Fertilizer record
    # is allowed.
    #
    # ======================================================

    schedule_df = (
        deduplicate_fertilizer_schedule(
            schedule_df
        )
    )

    # ======================================================
    # LOAD ACTUAL FERTILIZER APPLICATIONS
    # ======================================================

    actual_df = pd.DataFrame()

    if os.path.exists(
        FERTILIZER_FILE
    ):

        actual_df = pd.read_excel(
            FERTILIZER_FILE
        )

        # --------------------------------------------------
        # SEASON FILTER
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

            actual_df[
                "_ApplicationDate"
            ] = pd.to_datetime(
                actual_df["Date"],
                errors="coerce"
            )

        else:

            actual_df[
                "_ApplicationDate"
            ] = pd.NaT

    # ======================================================
    # PREPARE PROGRAMME RECORDS
    # ======================================================

    records = schedule_df.to_dict(
        orient="records"
    )

    # ======================================================
    # NORMALISE PROGRAMME RECORDS
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

    for index, record in enumerate(
        records
    ):

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

            programme_groups[
                group_key
            ] = []

        programme_groups[
            group_key
        ].append(index)

    # ==================================================
    # PROCESS EACH FIELD + FERTILIZER
    # ==================================================
    #
    # IMPORTANT:
    #
    # The fertilizer programme defines what is PLANNED.
    #
    # The actual fertilizer records define:
    #
    #     - what was actually applied
    #     - how much was applied
    #     - the actual application date
    #
    # Fertilizer names are NOT hard-coded as Basal or
    # Top Dressing here.
    #
    # This is important because the DCGL fertilizer
    # programme may change from season to season.
    #
    # Example:
    #
    # Season 1:
    #     BASAL = DAP + MOP + ZINC
    #     TOP    = UREA + SA
    #
    # Season 2:
    #     BASAL = DAP + SA + ZINC
    #     TOP    = UREA + MOP
    #
    # The actual fertilizer records are always captured
    # regardless of which stage the fertilizer was planned
    # for.
    #
    # ==================================================

    for (
            field,
            fertilizer
    ), group_indexes in programme_groups.items():

        if not group_indexes:
            continue

        # ==================================================
        # GROUP RECORDS
        # ==================================================

        group_records = [
            records[index]
            for index in group_indexes
        ]

        # ==================================================
        # FIND ACTUAL APPLICATIONS
        # ==================================================
        #
        # IMPORTANT:
        #
        # We deliberately do NOT filter these applications
        # based on the Basal date.
        #
        # If SA was actually applied on the Basal date,
        # that actual SA date must still be captured.
        #
        # If MOP was actually applied before the planned
        # Top Dressing date, that actual date must still
        # be captured.
        #
        # The actual record is the source of truth.
        #
        # ==================================================

        actual_applications = (
            get_actual_fertilizer_applications(
                actual_df,
                field,
                fertilizer
            )
        )

        # ==================================================
        # FIND ACTUAL BASAL DATE
        # ==================================================
        #
        # This is retained for calculating the NORMAL
        # planned Top Dressing dates.
        #
        # It is NOT used to reject actual fertilizer
        # applications.
        #
        # ==================================================

        basal_date = get_field_basal_date(
            actual_df,
            field
        )

        # ==================================================
        # IDENTIFY PROGRAMME STAGES
        # ==================================================

        basal_indexes = []
        top1_index = None
        top2_index = None
        other_indexes = []

        for index in group_indexes:

            operation = normalize_operation_name(
                records[index].get(
                    "Operation",
                    ""
                )
            )

            if operation == "BASAL APPLICATION":

                basal_indexes.append(index)

            elif operation == "TOP DRESSING 1":

                top1_index = index

            elif operation == "TOP DRESSING 2":

                top2_index = index

            else:

                other_indexes.append(index)

        # ==================================================
        # PROGRAMME STAGE ORDER
        # ==================================================
        #
        # Actual applications are assigned chronologically
        # to the available programme stages.
        #
        # This means the actual record is never discarded
        # simply because its date was earlier than the
        # planned date.
        #
        # ==================================================

        stage_indexes = []

        # --------------------------------------------------
        # BASAL
        # --------------------------------------------------

        for index in basal_indexes:
            stage_indexes.append(index)

        # --------------------------------------------------
        # TOP DRESSING 1
        # --------------------------------------------------

        if top1_index is not None:
            stage_indexes.append(
                top1_index
            )

        # --------------------------------------------------
        # TOP DRESSING 2
        # --------------------------------------------------

        if top2_index is not None:
            stage_indexes.append(
                top2_index
            )

        # --------------------------------------------------
        # OTHER / MANUAL PROGRAMME
        # --------------------------------------------------

        for index in other_indexes:
            stage_indexes.append(index)

        # ==================================================
        # UREA / SA PROGRAMME QUANTITY
        # ==================================================
        #
        # Both UREA and SA are calculated from:
        #
        #     Rate × Programme Area
        #
        # Where Top Dressing 1 and Top Dressing 2 have
        # separate rates:
        #
        #     Total = Area × (Top 1 Rate + Top 2 Rate)
        #
        # The total requirement is then split between
        # Top Dressing 1 and Top Dressing 2.
        #
        # Example:
        #
        #     Area = 3.0 ha
        #     SA Top 1 = 2 bags/ha
        #     SA Top 2 = 2 bags/ha
        #
        #     Total = 3 × (2 + 2)
        #           = 12 bags
        #
        #     Top 1 = 6 bags
        #     Top 2 = 6 bags
        #
        # If total is odd:
        #
        #     15 -> 7 + 8
        #
        # The first actual application can redefine the
        # Top 1 quantity, with the remaining requirement
        # automatically assigned to Top 2.
        #
        # UREA and SA are processed independently.
        #
        # ==================================================

        if fertilizer in (
                "UREA",
                "SA"
        ):

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

            # ------------------------------------------------
            # DCGL AREA RULE
            # ------------------------------------------------

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

            # ------------------------------------------------
            # FIND TOP 1 / TOP 2 RATES
            # ------------------------------------------------

            top1_rate = 0
            top2_rate = 0

            for record in group_records:

                operation = normalize_operation_name(
                    record.get(
                        "Operation",
                        ""
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

            # ------------------------------------------------
            # TOTAL REQUIREMENT
            # ------------------------------------------------

            total_rate = (
                    top1_rate
                    +
                    top2_rate
            )

            if (
                    programme_area > 0
                    and total_rate > 0
            ):

                total_requirement = whole_bags(
                    programme_area
                    * total_rate
                )

            else:

                total_requirement = 0

            # ------------------------------------------------
            # DEFAULT SPLIT
            #
            # Example:
            #
            # 15 -> 7 + 8
            # 12 -> 6 + 6
            #
            # ------------------------------------------------

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

            # ------------------------------------------------
            # ACTUAL FIRST APPLICATION
            #
            # If an actual first application exists,
            # use its actual quantity for Top 1.
            #
            # The remaining requirement becomes Top 2.
            #
            # Example:
            #
            # Total = 15
            # Actual Top 1 = 8
            #
            # Top 1 = 8
            # Top 2 = 7
            #
            # This works independently for UREA and SA.
            # ------------------------------------------------

            if actual_applications:

                first_actual_quantity = whole_bags(
                    actual_applications[0].get(
                        "quantity",
                        0
                    )
                )

                if (
                        first_actual_quantity > 0
                        and
                        first_actual_quantity < total_requirement
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
        #
        # Actual applications are assigned in chronological
        # order to the programme stages.
        #
        # This is the key change.
        #
        # ==================================================

        for stage_number, index in enumerate(
                stage_indexes
        ):

            record = records[index]

            operation = normalize_operation_name(
                record.get(
                    "Operation",
                    ""
                )
            )

            # ------------------------------------------------
            # PLANNED QUANTITY
            # ------------------------------------------------
            #
            # UREA and SA use the calculated total requirement
            # and are split between Top Dressing 1 and Top
            # Dressing 2.
            #
            # ------------------------------------------------

            if (
                    fertilizer in (
                    "UREA",
                    "SA"
            )
                    and
                    operation == "TOP DRESSING 1"
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
                    operation == "TOP DRESSING 2"
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

            # ------------------------------------------------
            # ACTUAL APPLICATION
            # ------------------------------------------------
            #
            # ACTUAL FERTILIZER IS THE SOURCE OF TRUTH.
            #
            # IMPORTANT:
            #
            # A fertilizer may be applied in several parts.
            #
            # Example:
            #
            #     Planned DAP Basal = 6 bags
            #
            #     01 July = 5 bags
            #     15 July = 1 bag
            #
            #     Total Actual = 6 bags
            #
            # Therefore:
            #
            #     Balance = 0
            #     Status  = APPLIED
            #
            # For a BASAL-ONLY fertilizer, ALL actual
            # applications are cumulative against the
            # Basal requirement.
            #
            # For fertilizers having Top Dressing stages,
            # the existing chronological stage allocation
            # remains unchanged.
            #
            # ------------------------------------------------

            # ==================================================
            # BASAL-ONLY FERTILIZER
            # ==================================================
            #
            # If this fertilizer has a Basal programme stage
            # but does NOT have Top Dressing 1 or 2, all actual
            # applications belong to the Basal requirement.
            #
            # ==================================================

            if (
                    operation == "BASAL APPLICATION"
                    and
                    top1_index is None
                    and
                    top2_index is None
            ):

                # ------------------------------------------------
                # SUM ALL ACTUAL APPLICATIONS
                # ------------------------------------------------

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

                # ------------------------------------------------
                # USE THE MOST RECENT ACTUAL DATE
                # ------------------------------------------------
                #
                # The latest date represents the date on which
                # the planned quantity was most recently updated.
                #
                # Example:
                #
                # 5 bags -> 01 July
                # 1 bag  -> 15 July
                #
                # Actual Date = 15 July
                #
                # ------------------------------------------------

                if actual_applications:

                    actual_date = (
                        actual_applications[-1].get(
                            "date"
                        )
                    )

                else:

                    actual_date = None

            # ==================================================
            # NORMAL STAGE-BY-STAGE PROCESSING
            # ==================================================
            #
            # Used for:
            #
            #     BASAL + TOP 1
            #     BASAL + TOP 1 + TOP 2
            #     TOP 1 + TOP 2
            #     Other programme stages
            #
            # ==================================================

            else:

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

            # ------------------------------------------------
            # UPDATE RECORD
            # ------------------------------------------------

            update_fertilizer_record(
                record,
                planned,
                actual,
                actual_date
            )

        # ==================================================
        # CALCULATE PLANNED TOP DRESSING DATES
        # ==================================================
        #
        # These dates are PLAN dates only.
        #
        # They do not override actual application dates.
        #
        # ==================================================

        if top1_index is not None:

            top1_record = records[
                top1_index
            ]

            # ------------------------------------------------
            # TOP 1 DEFAULT PLANNED DATE
            # ------------------------------------------------

            if basal_date is not None:

                planned_top1_date = (
                    get_top_dressing_date(
                        basal_date
                    )
                )

                if planned_top1_date is not None:
                    top1_record[
                        "Planned Date"
                    ] = planned_top1_date.strftime(
                        "%Y-%m-%d"
                    )

        # ==================================================
        # TOP DRESSING 2 PLANNED DATE
        # ==================================================
        #
        # If the actual first application exists, Top 2 is
        # planned 28 days after that actual application.
        #
        # Otherwise use Basal + 56 days.
        #
        # ==================================================

        if top2_index is not None:

            top2_record = records[
                top2_index
            ]

            if len(actual_applications) >= 1:

                actual_top1_date = pd.to_datetime(
                    actual_applications[0].get(
                        "date"
                    ),
                    errors="coerce"
                )

                if pd.notna(
                        actual_top1_date
                ):
                    next_top_date = (
                            actual_top1_date
                            + pd.Timedelta(
                        days=28
                    )
                    )

                    top2_record[
                        "Planned Date"
                    ] = next_top_date.strftime(
                        "%Y-%m-%d"
                    )

            elif basal_date is not None:

                basal_date_value = pd.to_datetime(
                    basal_date,
                    errors="coerce"
                )

                if pd.notna(
                        basal_date_value
                ):
                    default_top2_date = (
                            basal_date_value
                            + pd.Timedelta(
                        days=56
                    )
                    )

                    top2_record[
                        "Planned Date"
                    ] = default_top2_date.strftime(
                        "%Y-%m-%d"
                    )

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

    # ======================================================
    # REMINDERS
    # ======================================================

    reminders = records

    # ======================================================
    # SORTING
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

    reminders.sort(
        key=lambda x: (
            status_order.get(
                x.get(
                    "Status"
                ),
                99
            ),
            str(
                x.get(
                    "Estate",
                    ""
                )
            ),
            str(
                x.get(
                    "Field",
                    ""
                )
            ),
            str(
                x.get(
                    "Planned Date",
                    ""
                )
            ),
            str(
                x.get(
                    "Operation",
                    ""
                )
            ),
            str(
                x.get(
                    "Fertilizer",
                    ""
                )
            )
        )
    )

    # ======================================================
    # SUMMARY COUNTS
    # ======================================================

    reminder_summary = get_fertilizer_schedule_summary(
        season
    )

    # ======================================================
    # RENDER
    # ======================================================

    return render_template(
        "agriculture/fertilizer_schedule.html",
        season=season,
        reminders=reminders,
        reminder_summary=reminder_summary
    )


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

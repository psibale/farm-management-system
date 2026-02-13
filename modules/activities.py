from flask import Blueprint, render_template, session, redirect, url_for, request, flash
import os
import pandas as pd
from modules.helpers import get_active_season  # assuming you're using helper functions
from modules.utils import role_required
import json
from modules.gdrive_sync import upload_excel_to_drive
from flask import request, jsonify

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
        flash("No planting records found.", "warning")
        return redirect(url_for('agriculture.planting'))

    df = pd.read_excel(PLANTING_FILE)

    if "Season" not in df.columns:
        flash("No 'Season' column found in data.", "danger")
        return redirect(url_for('agriculture.planting'))

    # Get list of available seasons from file
    seasons = sorted(df["Season"].dropna().unique().tolist())

    # Determine which season to view
    selected_season = request.form.get("season") or seasons[-1]  # default to latest season

    # Filter data
    df = df[df["Season"] == selected_season]

    if df.empty:
        flash(f"No planting data found for season {selected_season}.", "info")
        return redirect(url_for('agriculture.planting'))

    # Ensure numeric columns
    labor_cols = ["Capitao", "Planters", "Choppers", "Gleaners", "Water Drawers", "Tools Keeper", "Transporters"]
    for col in labor_cols + ["Planted Area (ha)", "Bundles Used"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculations
    total_dates = df['Date'].nunique()
    total_area = df['Planted Area (ha)'].sum()
    total_bundles = df['Bundles Used'].sum() if 'Bundles Used' in df.columns else 0
    labor_totals = {col: df[col].sum() for col in labor_cols if col in df.columns}
    total_labor = sum(labor_totals.values())

    return render_template("agriculture/planting_report.html",
                           seasons=seasons,
                           selected_season=selected_season,
                           total_dates=total_dates,
                           total_area=total_area,
                           total_bundles=total_bundles,
                           labor_totals=labor_totals,
                           total_labor=total_labor)



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

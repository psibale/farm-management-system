# agriculture.py - Flask Blueprint for agriculture Module

from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import base64
from modules.utils import role_required
# ✅ Define blueprint BEFORE routes
agriculture_bp = Blueprint("agriculture", __name__, template_folder="../templates/agriculture")



REGISTRATION_FILE = "data/registered_fields.xlsx"
PLANTING_FILE = "data/planting_records.xlsx"
SEASON_FILE = "active_season.txt"
FIELD_REGISTRATION_FILE = "data/registered_fields.xlsx"
CROP_ESTIMATE_FILE = "data/crop_estimates.xlsx"
YIELD_FILE = "data/yield_data.xlsx"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def get_active_season():
    try:
        with open(SEASON_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "2024/25"

@agriculture_bp.route('/')
def agriculture_home():
    return render_template("agriculture/home.html", season=get_active_season())


@agriculture_bp.route('/fields', methods=['GET', 'POST'])
def registered_fields():
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == 'POST':
        # Process form submission
        main_field = request.form['main_field']
        field = request.form['field']
        grower = request.form['grower']
        hectares = request.form['hectares']

        df = pd.read_excel(FIELD_REGISTRATION_FILE) if os.path.exists(FIELD_REGISTRATION_FILE) else pd.DataFrame(
            columns=["Main Field", "Field", "Growers Name", "Hectares", "Season"])

        new_row = {
            "Main Field": main_field,
            "Field": field,
            "Growers Name": grower,
            "Hectares": float(hectares),
            "Season": season
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(FIELD_REGISTRATION_FILE, index=False)

        flash("Field registered successfully!", "success")
        return redirect(url_for("agriculture.registered_fields"))

    # GET request: show form and existing fields
    if os.path.exists(FIELD_REGISTRATION_FILE):
        df = pd.read_excel(FIELD_REGISTRATION_FILE)
        df = df[df["Season"] == season] if "Season" in df.columns else df
    else:
        df = pd.DataFrame()

    return render_template("agriculture/field_registration.html", fields=df.to_dict(orient='records'), season=season)


@agriculture_bp.route('/planting', methods=['GET', 'POST'])
def planting():
    from modules.season import get_active_season
    season = get_active_season()

    if request.method == 'POST':
        field = request.form['Field']
        crop = request.form['Crop Type']
        date = request.form['Date']

        if not os.path.exists(PLANTING_FILE):
            df = pd.DataFrame(columns=["Field", "Crop", "Date", "Season"])
        else:
            df = pd.read_excel(PLANTING_FILE)

        df = pd.concat([df, pd.DataFrame.from_records([{
            "Field": field,
            "Crop": crop,
            "Date": date,
            "Season": season
        }])], ignore_index=True)

        df.to_excel(PLANTING_FILE, index=False)
        flash("Planting record saved.", "success")
        return redirect(url_for('agriculture.planting'))

    return render_template("agriculture/planting.html", season=season)

@agriculture_bp.route("/crop-estimates", methods=["GET", "POST"])
def crop_estimates():
    from modules.season import get_active_season
    season = get_active_season()

    CROP_ESTIMATE_FILE = "data/crop_estimates.xlsx"
    REGISTERED_FIELDS_FILE = "data/registered_fields.xlsx"
    fields = ["Date", "Field", "Crop", "TCH", "Estimated Yield (Tons)", "Area (ha)", "Remarks", "Season"]

    # Load existing estimates
    if os.path.exists(CROP_ESTIMATE_FILE):
        df = pd.read_excel(CROP_ESTIMATE_FILE)
        df = df[df["Season"] == season]
        crop_data = df.to_dict(orient="records")
    else:
        crop_data = []

    # Load field-to-area mapping
    if os.path.exists(REGISTERED_FIELDS_FILE):
        df_fields = pd.read_excel(REGISTERED_FIELDS_FILE)
        # Normalize to main fields (e.g., DG01000)
        df_fields["Main Field"] = df_fields["Field"].astype(str).str[:-2] + "00"
        area_sums = df_fields.groupby("Main Field")["Hectares"].sum().round(3).to_dict()
        field_area_map = area_sums  # now keyed by main field like DG01000
    else:
        field_area_map = {}

    if request.method == "POST":
        try:
            data = {
                "Date": request.form.get("Date"),
                "Field": request.form.get("Field"),
                "Crop": request.form.get("Crop"),
                "TCH": float(request.form.get("TCH")),
                "Remarks": request.form.get("Remarks"),
                "Season": season
            }

            # Get area from registered fields
            area = field_area_map.get(data["Field"])
            if area is None:
                raise ValueError("Area not found for selected field.")

            data["Area (ha)"] = area
            data["Estimated Yield (Tons)"] = round(data["TCH"] * area, 2)

            if os.path.exists(CROP_ESTIMATE_FILE):
                df = pd.read_excel(CROP_ESTIMATE_FILE)
            else:
                df = pd.DataFrame(columns=fields)

            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(CROP_ESTIMATE_FILE, index=False)

            flash("Crop estimate saved successfully!", "success")
            return redirect(url_for("agriculture.crop_estimates"))

        except Exception as e:
            flash(f"Failed to save: {e}", "danger")

    return render_template("agriculture/crop_estimate.html",
                           season=season,
                           crop_data=crop_data,
                           field_area_map=field_area_map)


CROP_ESTIMATE_FILE = "data/crop_estimates.xlsx"
YIELD_FILE = "data/yield_data.xlsx"

@agriculture_bp.route('/estimate-progress')
def crop_estimate_progress():
    try:
        from modules.season import get_active_season
        season = request.args.get("season")
        if not season:
            with open("data/active_season.txt") as f:
                season = f.read().strip()

        # Check file existence
        if not os.path.exists(CROP_ESTIMATE_FILE) or not os.path.exists(YIELD_FILE):
            return render_template("agriculture/crop_estimate_progress.html", error="Missing data files.", season=season)

        # Load data
        df_est = pd.read_excel(CROP_ESTIMATE_FILE)
        df_yld = pd.read_excel(YIELD_FILE)

        df_est = df_est[df_est["Season"] == season]
        df_yld = df_yld[df_yld["Season"] == season]

        if df_est.empty:
            return render_template("agriculture/crop_estimate_progress.html", error=f"No crop estimates for {season}", season=season)

        # Normalize fields
        df_est["Main Field"] = df_est["Field"].astype(str).str[:-2] + "00"
        df_yld["Main Field"] = df_yld["Field"].astype(str).str[:-2] + "00"

        # Calculate Estimated Yield if not already done
        df_est["Estimated Yield (Tons)"] = df_est["TCH"] * df_est["Area (ha)"]

        # Group estimates
        est_grouped = df_est.groupby(["Main Field", "Crop"]).agg({
            "TCH": "mean",
            "Area (ha)": "sum",
            "Estimated Yield (Tons)": "sum"
        }).reset_index()

        # Group actual yield
        yld_grouped = df_yld.groupby(["Main Field", "Crop"]).agg({
            "Yield (Tons)": "sum"
        }).reset_index()

        # Merge and compute comparisons
        merged = pd.merge(est_grouped, yld_grouped, on=["Main Field", "Crop"], how="left").fillna(0)
        merged["Progress (%)"] = (merged["Yield (Tons)"] / merged["Estimated Yield (Tons)"] * 100).round(2)
        merged["Difference (Tons)"] = (merged["Yield (Tons)"] - merged["Estimated Yield (Tons)"]).round(2)
        merged["Difference (%)"] = (merged["Difference (Tons)"] / merged["Estimated Yield (Tons)"] * 100).round(2)
        merged["Actual TCH"] = (merged["Yield (Tons)"] / merged["Area (ha)"]).round(2)

        # Summary
        total_estimate = merged["Estimated Yield (Tons)"].sum()
        total_yield = merged["Yield (Tons)"].sum()
        overall_progress = round((total_yield / total_estimate * 100), 2) if total_estimate else 0

        # Crop-level summary
        crop_summary = merged.groupby("Crop").agg({
            "Estimated Yield (Tons)": "sum",
            "Yield (Tons)": "sum"
        }).reset_index()

        crop_progress = []
        for _, row in crop_summary.iterrows():
            est = row["Estimated Yield (Tons)"]
            actual = row["Yield (Tons)"]
            progress = round((actual / est) * 100, 2) if est else 0
            crop_progress.append({
                "crop": row["Crop"],
                "estimate": est,
                "yield": actual,
                "progress": progress
            })

        return render_template("agriculture/crop_estimate_progress.html",
                               season=season,
                               summary={
                                   "total_estimate": round(total_estimate, 2),
                                   "total_yield": round(total_yield, 2),
                                   "overall_progress": overall_progress
                               },
                               crop_progress=crop_progress,
                               records=merged.to_dict(orient="records"))

    except Exception as e:
        return render_template("agriculture/crop_estimate_progress.html", error=str(e), season="N/A")


@agriculture_bp.route('/tractors', methods=['GET', 'POST'])
def tractor_operations():
    from modules.season import get_active_season
    season = get_active_season()
    excel_path = 'data/tractor_operations.xlsx'

    # Load existing data or initialize an empty DataFrame
    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()  # Remove extra spaces
        if 'Season' in df.columns:
            df = df[df['Season'] == season]
    else:
        df = pd.DataFrame(columns=[
            'Date', 'Field', 'Activity', 'Tractor Number', 'Operator',
            'Fuel Used', 'Hours Worked', 'Hour Meter Open', 'Hour Meter Closed', 'Season'
        ])

    if request.method == 'POST':
        try:
            open_hour = float(request.form.get('Hour Meter Open', 0))
            close_hour = float(request.form.get('Hour Meter Closed', 0))
            area = float(request.form.get('Area', 0))
            fuel_used = float(request.form.get('Fuel Used', 0))

            hours_worked = round(close_hour - open_hour, 2)
            fuel_per_ha = round(fuel_used / area, 2) if area else 0
            hours_per_ha = round(hours_worked / area, 2) if area else 0

            new_row = {
                'Date': request.form.get('Date'),
                'Tractor Number': request.form.get('Tractor Number'),
                'Operator': request.form.get('Operator'),
                'Field': request.form.get('Field'),
                'Activity': request.form.get('Activity'),
                'Hour Meter Open': open_hour,
                'Hour Meter Closed': close_hour,
                'Hours Worked': hours_worked,
                'Fuel Used': fuel_used,
                'Area': area,
                'Fuel per ha': fuel_per_ha,
                'Hours per ha': hours_per_ha,
                'Remarks': request.form.get('Remarks'),
                'Season': season
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(excel_path, index=False)
            flash('Tractor operation saved successfully!', 'success')
            return redirect(url_for('agriculture.tractor_operations'))

        except Exception as e:
            flash(f"Failed to save record: {e}", "danger")

    return render_template('agriculture/tractor_operations.html',
                           season=season,
                           records=df.to_dict(orient='records'))

DATA_FOLDER = 'data'

@agriculture_bp.route('/field-reports', methods=['GET'])
def field_reports():
    selected_field = request.args.get('field')
    season = request.args.get('season')
    report_ready = False

    # Load all distinct fields for dropdown
    all_fields = set()
    def get_unique_fields(filename):
        path = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(path):
            try:
                return pd.read_excel(path)['Field'].dropna().unique().tolist()
            except: return []
        return []

    for file in ["tractor_operations.xlsx", "harvesting_records.xlsx", "yield_data.xlsx",
                 "irrigation.xlsx", "pest_disease.xlsx", "weeding.xlsx",
                 "planting.xlsx", "herbicide.xlsx", "fertilizer.xlsx"]:
        all_fields.update(get_unique_fields(file))

    all_fields = sorted(all_fields)

    def load_filtered_data(filename, filters):
        path = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(path):
            df = pd.read_excel(path)
            for col, val in filters.items():
                if val and col in df.columns:
                    df = df[df[col] == val]
            return df.to_dict('records')
        return []

    if selected_field:
        filters = {'Field': selected_field}
        if season:
            filters['Season'] = season
        report_ready = True

        tractor_data = load_filtered_data('tractor_operations.xlsx', filters)
        harvesting_data = load_filtered_data('harvesting_records.xlsx', filters)
        haulage_data = load_filtered_data('yield_data.xlsx', filters)
        irrigation_data = load_filtered_data('irrigation.xlsx', filters)
        pest_data = load_filtered_data('pest_disease.xlsx', filters)
        weeding_data = load_filtered_data('weeding.xlsx', filters)
        planting_data = load_filtered_data('planting.xlsx', filters)
        herbicide_data = load_filtered_data('herbicide.xlsx', filters)
        fertilizer_data = load_filtered_data('fertilizer.xlsx', filters)
    else:
        tractor_data = harvesting_data = haulage_data = irrigation_data = []
        pest_data = weeding_data = planting_data = herbicide_data = fertilizer_data = []

    return render_template('agriculture/field_report.html',
                           fields=all_fields,
                           selected_field=selected_field,
                           season=season,
                           report_ready=report_ready,
                           tractor_data=tractor_data,
                           harvesting_data=harvesting_data,
                           haulage_data=haulage_data,
                           irrigation_data=irrigation_data,
                           pest_data=pest_data,
                           weeding_data=weeding_data,
                           planting_data=planting_data,
                           herbicide_data=herbicide_data,
                           fertilizer_data=fertilizer_data)

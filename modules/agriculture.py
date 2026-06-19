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
from flask import render_template, request, redirect, flash, url_for
# ✅ Define blueprint BEFORE routes
agriculture_bp = Blueprint("agriculture", __name__, template_folder="../templates/agriculture")



REGISTRATION_FILE = "data/registered_fields.xlsx"
PLANTING_FILE = "data/planting_records.xlsx"
SEASON_FILE = "active_season.txt"
FIELD_REGISTRATION_FILE = "data/registered_fields.xlsx"
CROP_ESTIMATE_FILE = "data/crop_estimates.xlsx"
YIELD_FILE = "data/yield_data.xlsx"
CROP_REGISTER_FILE = "data/crop_register.xlsx"
CROP_FILE = "data/crop_register.xlsx"
VARIETY_FILE = "data/crop_varieties.xlsx"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def get_active_season():
    try:
        with open(SEASON_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "2024/25"

def get_parent_block(field_code):
    """
    DG01001 → DG01000
    DG01000 → DG01000
    """
    if field_code and field_code[-2:].isdigit():
        return field_code[:-2] + "00"
    return field_code

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
    else:
        df = pd.DataFrame(columns=[
            'Date', 'Field', 'Activity', 'Tractor Number', 'Operator',
            'Fuel Used', 'Hours Worked', 'Hour Meter Open', 'Hour Meter Closed',
            'Area (ha)', 'Fuel per ha', 'Hours per ha', 'Remarks', 'Season'
        ])

    if request.method == 'POST':
        try:
            open_hour = float(request.form.get('Hour Meter Open', 0))
            close_hour = float(request.form.get('Hour Meter Closed', 0))
            area = float(request.form.get('Area (ha)', 0))
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
                'Area (ha)': area,
                'Fuel per ha': fuel_per_ha,
                'Hours per ha': hours_per_ha,
                'Remarks': request.form.get('Remarks'),
                'Season': season  # <- automatically assigned
            }

            # Append the new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(excel_path, index=False)
            flash('Tractor operation saved successfully!', 'success')
            return redirect(url_for('agriculture.tractor_operations'))

        except Exception as e:
            flash(f"Failed to save record: {e}", "danger")


    return render_template(
        'agriculture/tractor_operations.html',
        season=season

    )
@agriculture_bp.route('/tractor-report')
def tractor_operations_report():
    from modules.season import get_active_season
    season = get_active_season()

    excel_path = 'data/tractor_operations.xlsx'

    # Return empty template if file missing
    if not os.path.exists(excel_path):
        return render_template(
            'agriculture/tractor_operations_report.html',
            records=[],
            activity_fuel_summary=[],
            chart_data=[],
            fuel_chart_data=[],
            grouped_by_tractor=[],
            total_fuel=0,
            total_hours=0,
            total_area=0,
            average_fuel_per_ha=0,
            average_hours_per_ha=0,
            most_frequent_activity="N/A",
            average_hours_per_day=0,
            season=season
        )

    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()
    df['Activity'] = df['Activity'].astype(str).str.strip()
    df['Season'] = df['Season'].astype(str).str.strip()
    df['Tractor Number'] = df['Tractor Number'].astype(str).str.strip()

    display_df = df[df['Season'] == str(season)].copy()

    # ================== APPLY FILTERS ==================
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tractor = request.args.get('tractor')

    display_df['Date'] = pd.to_datetime(display_df['Date'], errors='coerce')

    if start_date:
        start_date = pd.to_datetime(start_date)
        display_df = display_df[display_df['Date'] >= start_date]

    if end_date:
        end_date = pd.to_datetime(end_date)
        display_df = display_df[display_df['Date'] <= end_date]

    if tractor:
        display_df = display_df[
            display_df['Tractor Number'].str.contains(tractor, case=False, na=False)
        ]

    # ================== CLEAN NUMERIC COLUMNS ==================
    numeric_cols = ['Fuel Used', 'Hours Worked', 'Area (ha)']
    for col in numeric_cols:
        if col not in display_df.columns:
            display_df[col] = 0
    display_df[numeric_cols] = display_df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # ================== DASHBOARD METRICS ==================
    total_fuel = round(display_df['Fuel Used'].sum(), 2)
    total_hours = round(display_df['Hours Worked'].sum(), 2)
    total_area = round(display_df['Area (ha)'].sum(), 2)

    average_fuel_per_ha = round(total_fuel / total_area, 2) if total_area else 0
    average_hours_per_ha = round(total_hours / total_area, 2) if total_area else 0

    # ================== ACTIVITY FUEL SUMMARY ==================
    if not display_df.empty and 'Activity' in display_df.columns:
        summary_df = (
            display_df.groupby('Activity')
            .agg({
                'Fuel Used': ['sum', 'mean'],
                'Hours Worked': 'sum',
                'Area (ha)': 'sum'
            })
            .reset_index()
        )
        summary_df.columns = ['Activity', 'Total_Fuel', 'Average_Fuel', 'Total_Hours', 'Total_Area']
        summary_df['Average_Fuel'] = summary_df['Average_Fuel'].round(2)
        activity_fuel_summary = summary_df.to_dict(orient='records')
        most_frequent_activity = display_df['Activity'].value_counts().idxmax()
    else:
        activity_fuel_summary = []
        most_frequent_activity = "N/A"

    # ================== CHART DATA ==================
    chart_data = (
        display_df.groupby('Activity')['Hours Worked']
        .sum()
        .reset_index()
        .to_dict(orient='records') if not display_df.empty else []
    )

    fuel_chart_data = (
        display_df.groupby('Tractor Number')['Fuel Used']
        .sum()
        .reset_index()
        .to_dict(orient='records') if not display_df.empty else []
    )

    grouped_by_tractor = (
        display_df.groupby('Tractor Number')
        .agg({
            'Hours Worked': 'sum',
            'Fuel Used': 'sum',
            'Area (ha)': 'sum'
        })
        .reset_index()
        .to_dict(orient='records') if not display_df.empty else []
    )

    days = display_df['Date'].nunique() if not display_df.empty else 0
    average_hours_per_day = round(total_hours / days, 2) if days else 0

    return render_template(
        'agriculture/tractor_operations_report.html',
        season=season,
        records=display_df.to_dict(orient='records'),
        total_fuel=total_fuel,
        total_hours=total_hours,
        total_area=total_area,
        average_fuel_per_ha=average_fuel_per_ha,
        average_hours_per_ha=average_hours_per_ha,
        activity_fuel_summary=activity_fuel_summary,
        chart_data=chart_data,
        fuel_chart_data=fuel_chart_data,
        grouped_by_tractor=grouped_by_tractor,
        most_frequent_activity=most_frequent_activity,
        average_hours_per_day=average_hours_per_day
    )

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
            except:
                return []
        return []

    for file in [
        "tractor_operations.xlsx", "harvesting_records.xlsx", "yield_data.xlsx",
        "irrigation_records.xlsx", "pest_disease_control.xlsx",  # added control file
        "weeding_records.xlsx", "planting_records.xlsx", "herbicide_records.xlsx", "fertilizer_records.xlsx"
    ]:
        all_fields.update(get_unique_fields(file))

    all_fields = sorted(all_fields)

    def load_filtered_data(filename, filters):
        path = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(path):
            df = pd.read_excel(path)
            for col, val in filters.items():
                if val and col in df.columns:
                    df = df[df[col] == val]
            return df
        return pd.DataFrame()

    if selected_field:
        filters = {'Field': selected_field}
        if season:
            filters['Season'] = season
        report_ready = True

        tractor_data = load_filtered_data('tractor_operations.xlsx', filters).to_dict('records')
        harvesting_data = load_filtered_data('harvesting_records.xlsx', filters).to_dict('records')
        haulage_data = load_filtered_data('yield_data.xlsx', filters).to_dict('records')
        # 🌧️ Irrigation (include block-level records)
        irrigation_path = os.path.join(DATA_FOLDER, 'irrigation_records.xlsx')
        irrigation_df = pd.DataFrame()

        if os.path.exists(irrigation_path):
            irrigation_df = pd.read_excel(irrigation_path)

            parent_block = get_parent_block(selected_field)

            if 'Field' in irrigation_df.columns:
                irrigation_df = irrigation_df[
                    irrigation_df['Field'].isin([selected_field, parent_block])
                ]

            if season and 'Season' in irrigation_df.columns:
                irrigation_df = irrigation_df[irrigation_df['Season'] == season]

            if 'Date' in irrigation_df.columns:
                irrigation_df = irrigation_df.sort_values(by='Date', ascending=False)

        irrigation_data = irrigation_df.to_dict('records')

        # 🐛 Pest & Disease Control (include block-level records)
        pest_control_path = os.path.join(DATA_FOLDER, 'pest_disease_control.xlsx')
        pest_control_df = pd.DataFrame()

        if os.path.exists(pest_control_path):
            pest_control_df = pd.read_excel(pest_control_path)

            parent_block = get_parent_block(selected_field)

            if 'Field' in pest_control_df.columns:
                pest_control_df = pest_control_df[
                    pest_control_df['Field'].isin([selected_field, parent_block])
                ]

            if season and 'Season' in pest_control_df.columns:
                pest_control_df = pest_control_df[
                    pest_control_df['Season'] == season
                    ]

            cols_to_keep = [
                'Date', 'Field', 'SMUT%', 'YSA%', 'Black Beetles (ha)',
                'Lady Beetle', 'Hectares', 'Pesticide Used',
                'Liters', 'Mandays'
            ]
            pest_control_df = pest_control_df[
                [c for c in cols_to_keep if c in pest_control_df.columns]
            ]

            if 'Date' in pest_control_df.columns:
                pest_control_df = pest_control_df.sort_values(by='Date', ascending=False)

        pest_control_data = pest_control_df.to_dict('records')

        weeding_data = load_filtered_data('weeding_records.xlsx', filters).to_dict('records')
        herbicide_data = load_filtered_data('herbicide_records.xlsx', filters).to_dict('records')
        fertilizer_data = load_filtered_data('fertilizer_records.xlsx', filters).to_dict('records')

        # ✅ Planting report
        planting_path = os.path.join(DATA_FOLDER, 'planting_records.xlsx')
        planting_df = pd.DataFrame()
        if os.path.exists(planting_path):
            planting_df = pd.read_excel(planting_path)
            if 'Field' in planting_df.columns:
                planting_df = planting_df[planting_df['Field'] == selected_field]
            if season and 'Season' in planting_df.columns:
                planting_df = planting_df[planting_df['Season'] == season]
            if 'Date' in planting_df.columns:
                planting_df = planting_df.sort_values(by='Date', ascending=False)

        planting_data = planting_df.to_dict('records')
        planting_summary = {
            "total_dates": planting_df['Date'].nunique() if not planting_df.empty else 0,
            "total_area": planting_df['Planted Area (ha)'].sum() if 'Planted Area (ha)' in planting_df.columns else 0,
            "total_bundles": planting_df['Bundles Used'].sum() if 'Bundles Used' in planting_df.columns else 0,
            "total_labour": planting_df['Mandays'].sum() if 'Mandays' in planting_df.columns else 0
        }


        # Herbicide Application
        herbicide_df = load_filtered_data('herbicide_records.xlsx', filters)
        herbicide_data = herbicide_df.to_dict('records')

        if not herbicide_df.empty:
            herbicide_summary = {
                "total_dates": herbicide_df['Date'].nunique(),
                "total_area": herbicide_df[
                    'Applied Area (ha)'].sum() if 'Applied Area (ha)' in herbicide_df.columns else 0,
                "total_mandays": herbicide_df['Mandays'].sum() if 'Mandays' in herbicide_df.columns else 0
            }
        else:
            herbicide_summary = {
                "total_dates": 0,
                "total_area": 0,
                "total_mandays": 0
            }

        # Fertilizer Application
        fertilizer_df = load_filtered_data('fertilizer_records.xlsx', filters)
        fertilizer_data = fertilizer_df.to_dict('records')

        if not fertilizer_df.empty:
            fertilizer_summary = {
                "total_dates": fertilizer_df['Date'].nunique(),
                "total_area": fertilizer_df['Area (Ha)'].sum() if 'Area (Ha)' in fertilizer_df.columns else 0,
                "total_dap": fertilizer_df['DAP'].sum() if 'DAP' in fertilizer_df.columns else 0,
                "total_sa": fertilizer_df['SA'].sum() if 'SA' in fertilizer_df.columns else 0,
                "total_mop": fertilizer_df['MOP'].sum() if 'MOP' in fertilizer_df.columns else 0,
                "total_zinc": fertilizer_df['Zinc'].sum() if 'Zinc' in fertilizer_df.columns else 0,
                "total_urea": fertilizer_df['UREA'].sum() if 'UREA' in fertilizer_df.columns else 0,
                "total_mandays": fertilizer_df['Mandays'].sum() if 'Mandays' in fertilizer_df.columns else 0
            }
        else:
            fertilizer_summary = {
                "total_dates": 0,
                "total_area": 0,
                "total_dap": 0,
                "total_sa": 0,
                "total_mop": 0,
                "total_zinc": 0,
                "total_urea": 0,
                "total_mandays": 0
            }

    else:
        tractor_data = harvesting_data = haulage_data = irrigation_data = []
        pest_data = weeding_data = planting_data = herbicide_data = fertilizer_data = []
        planting_summary = {}
        pest_control_data = []

    return render_template(
        'agriculture/field_report.html',
        fields=all_fields,
        selected_field=selected_field,
        season=season,
        report_ready=report_ready,
        tractor_data=tractor_data,
        harvesting_data=harvesting_data,
        haulage_data=haulage_data,
        irrigation_data=irrigation_data,
        weeding_data=weeding_data,
        planting_data=planting_data,
        planting_summary=planting_summary,
        pest_control_data=pest_control_data,  # ✅ pass to template
        herbicide_data=herbicide_data,
        fertilizer_data=fertilizer_data
    )


@agriculture_bp.route("/agriculture/crops")
def crop_management():
    return render_template("agriculture/crop_management.html")

@agriculture_bp.route("/crop-register")
def crop_register():

    if os.path.exists(CROP_FILE):
        df = pd.read_excel(CROP_FILE)
        records = df.to_dict("records")
    else:
        records = []

    return render_template(
        "agriculture/crop_register.html",
        records=records
    )

@agriculture_bp.route("/add-crop", methods=["GET", "POST"])
def add_crop():

    if request.method == "POST":

        new_row = {
            "Field": request.form["field"],
            "Variety": request.form["variety"],
            "Planting Date": request.form["planting_date"],
            "Crop Cycle": request.form["crop_cycle"],
            "Status": request.form["status"],
            "Remarks": request.form["remarks"]
        }

        if os.path.exists(CROP_FILE):
            df = pd.read_excel(CROP_FILE)
            df = pd.concat(
                [df, pd.DataFrame([new_row])],
                ignore_index=True
            )
        else:
            df = pd.DataFrame([new_row])

        df.to_excel(CROP_FILE, index=False)

        flash("Crop record added successfully", "success")

        return redirect(
            url_for("agriculture.crop_register")
        )

    # Load active varieties for dropdown
    if os.path.exists(VARIETY_FILE):
        variety_df = pd.read_excel(VARIETY_FILE)

        varieties = (
            variety_df[
                variety_df["Status"] == "Active"
            ]["Variety"]
            .dropna()
            .sort_values()
            .tolist()
        )
    else:
        varieties = []

    return render_template(
        "agriculture/add_crop.html",
        varieties=varieties
    )

@agriculture_bp.route("/variety-management")
def variety_management():
    return render_template("variety_management.html")

@agriculture_bp.route("/add-variety", methods=["GET", "POST"])
def add_variety():

    if request.method == "POST":

        variety = request.form["variety"]
        maturity = request.form["maturity"]
        tch = request.form["tch"]
        status = request.form["status"]
        remarks = request.form["remarks"]

        new_row = {
            "Variety": variety,
            "Maturity Months": maturity,
            "Expected TCH": tch,
            "Status": status,
            "Remarks": remarks
        }

        if os.path.exists(VARIETY_FILE):
            df = pd.read_excel(VARIETY_FILE)
            df = pd.concat(
                [df, pd.DataFrame([new_row])],
                ignore_index=True
            )
        else:
            df = pd.DataFrame([new_row])

        df.to_excel(VARIETY_FILE, index=False)

        flash("Variety added successfully", "success")

        return redirect(
            url_for("agriculture.variety_register")
        )

    return render_template("add_variety.html")

@agriculture_bp.route("/variety-register")
def variety_register():

    if os.path.exists(VARIETY_FILE):
        df = pd.read_excel(VARIETY_FILE)
        records = df.to_dict("records")
    else:
        records = []

    return render_template(
        "variety_register.html",
        records=records
    )

@agriculture_bp.route("/crop-age-analysis")
def crop_age_analysis():

    if not os.path.exists(CROP_FILE):
        return render_template(
            "agriculture/crop_age_analysis.html",
            records=[]
        )

    df = pd.read_excel(CROP_FILE)

    records = []

    today = datetime.today()

    for _, row in df.iterrows():

        try:
            planting_date = pd.to_datetime(
                row["Planting Date"]
            )

            age_months = (
                (today.year - planting_date.year) * 12
                + today.month
                - planting_date.month
            )

        except:
            age_months = 0

        # Status Logic

        if age_months < 12:
            crop_status = "Growing"

        elif age_months < 18:
            crop_status = "Near Harvest"

        elif age_months <= 24:
            crop_status = "Harvest Ready"

        else:
            crop_status = "Overdue"

        records.append({
            "Field": row["Field"],
            "Variety": row["Variety"],
            "Planting Date": row["Planting Date"],
            "Crop Cycle": row["Crop Cycle"],
            "Age": age_months,
            "Status": crop_status
        })

    records = sorted(
        records,
        key=lambda x: x["Age"],
        reverse=True
    )

    return render_template(
        "agriculture/crop_age_analysis.html",
        records=records
    )
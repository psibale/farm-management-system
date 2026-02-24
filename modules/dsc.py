from flask import Blueprint, render_template, request
import pandas as pd
import os
from datetime import datetime
from flask import flash, render_template, request, redirect, url_for
from modules.season_utils import get_active_season
from modules.reporting_utils import get_reporting_range

dsc_bp = Blueprint('dsc', __name__)


# ---------------- VIEW RECORDS ----------------
def view_records(file_name):
    file_path = os.path.join('data', file_name)
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        return df.to_dict(orient='records')
    return []


# ---------------- SEASON FILTER ----------------
def load_season_filtered(file_path, season, month):
    """
    Loads file and filters strictly using reporting range
    for the active season + selected reporting month.
    """
    if not os.path.exists(file_path):
        return pd.DataFrame(), None, None

    start_date, end_date = get_reporting_range(season, month)

    df = pd.read_excel(file_path)

    if "Date" not in df.columns:
        return pd.DataFrame(), start_date, end_date

    df["Date"] = pd.to_datetime(df["Date"])

    df_filtered = df[
        (df["Date"] >= start_date) &
        (df["Date"] <= end_date)
    ]

    return df_filtered, start_date, end_date


# ---------------- SUMMARY HELPER ----------------
def prepare_summary(df, key_column, value_column):
    if df.empty or key_column not in df.columns or value_column not in df.columns:
        return {}

    totals = (
        df.groupby(key_column, dropna=False)
          .agg({value_column: 'sum'})
          .reset_index()
    )

    summary_dict = dict(zip(totals[key_column].astype(str), totals[value_column]))

    grand_total = df[value_column].sum()
    summary_dict["TOTAL"] = grand_total

    for k, v in summary_dict.items():
        if isinstance(v, (float, int)):
            summary_dict[k] = round(v, 2)

    return summary_dict


# ---------------- DSC DASHBOARD (SEASON BASED) ----------------
@dsc_bp.route('/')
def dsc_dashboard():

    activities = [
        {"name": "Cane Cutting", "file": "dsc_cane_cutting.xlsx", "link": "dsc.cane_cutting_form"},
        {"name": "Cane Shifting", "file": "dsc_cane_shifting.xlsx", "link": "dsc.cane_shifting_form"},
        {"name": "Cane Scraping", "file": "dsc_cane_scraping.xlsx", "link": "dsc.cane_scraping_form"},
        {"name": "Seedcane Cutting", "file": "dsc_seedcane_cutting.xlsx", "link": "dsc.seedcane_cutting_form"},
        {"name": "Seedcane Chopping", "file": "dsc_seedcane_chopping.xlsx", "link": "dsc.seedcane_chopping_form"},
        {"name": "Planting", "file": "dsc_planting.xlsx", "link": "dsc.planting_form"}
    ]

    # Selected reporting month (1–12)
    month = request.args.get('month', type=int) or datetime.now().month

    # Get active season
    season = get_active_season()

    summaries = []

    for act in activities:
        try:
            df_filtered, start_date, end_date = load_season_filtered(
                f"data/{act['file']}",
                season,
                month
            )

            summaries.append({
                "name": act["name"],
                "count": len(df_filtered),
                "link": act["link"]
            })

        except Exception as e:
            print(f"⚠️ Error loading {act['file']}: {e}")
            summaries.append({
                "name": act["name"],
                "count": 0,
                "link": act["link"]
            })

    # Get reporting period label for display
    try:
        start_date, end_date = get_reporting_range(season, month)
        reporting_label = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
    except:
        reporting_label = "Reporting period not configured"

    return render_template(
        "dsc_dashboard.html",
        summaries=summaries,
        active_season=season,
        selected_month=month,
        reporting_label=reporting_label
    )

from datetime import datetime
from flask import request, render_template, flash
from modules.season_utils import get_active_season
from modules.reporting_utils import get_reporting_range, load_and_filter


def handle_dsc_summary(file_path, title, group_field="Field", value_field="Bundles"):

    try:
        month = int(request.args.get('month', datetime.now().month))
        season = get_active_season()

        start_date, end_date = get_reporting_range(season, month)

        df_filtered = load_and_filter(
            file_path,
            start_date,
            end_date,
            season=season
        )

        if df_filtered.empty:
            flash("⚠️ No records found for this reporting period.", "warning")

        summary = prepare_summary(df_filtered, group_field, value_field)
        data_rows = df_filtered.to_dict(orient="records")

        return render_template(
            "dsc_generic_summary.html",
            title=title,
            summary=summary,
            data_rows=data_rows,
            active_season=season,
            selected_month=month,
            reporting_period={"start": start_date, "end": end_date}
        )

    except Exception as e:
        flash(f"Error generating summary: {e}", "danger")

        return render_template(
            "dsc_generic_summary.html",
            title=title,
            summary={},
            data_rows=[],
            active_season=None,
            selected_month=datetime.now().month,
            reporting_period=None
        )

@dsc_bp.route('/cane-cutting', methods=['GET', 'POST'])
def cane_cutting_form():

    from modules.season_utils import get_active_season

    file_path = 'data/dsc_cane_cutting.xlsx'
    season = get_active_season()

    columns = [
        'Season',  # ✅ add season column
        'Date', 'Field', 'Bundles Cut', 'Hectares', 'Variety',
        'Foreman', 'Capitaos', 'Water Drawers', 'Dippers',
        'Needlemen', 'Bicycle Guards', 'Feeder Breakers',
        'Cane Cutters', 'First-Aider', 'SHE Representative',
        'Tools Keeper', 'Tasker', 'Conductor', 'T/Transporter'
    ]

    if request.method == 'POST':

        data = {col: request.form.get(col, '') for col in columns}
        data['Season'] = season  # ✅ force active season

        if not data['Date'] or not data['Field'] or not data['Bundles Cut']:
            flash("Date, Field, and Bundles Cut are required.", "danger")
            return redirect(url_for('dsc.cane_cutting_form'))

        try:
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
            else:
                df = pd.DataFrame(columns=columns)

            for col in columns:
                if col not in df.columns:
                    df[col] = None

            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(file_path, index=False)

            flash("✅ Cane Cutting record saved successfully!", "success")

        except Exception as e:
            flash(f"❌ Error saving record: {e}", "danger")

        return redirect(url_for('dsc.cane_cutting_form'))

    return render_template(
        'dsc_cane_cutting_form.html',
        columns=columns,
        active_season=season
    )

@dsc_bp.route('/cane-cutting/view')
def dsc_cane_cutting_records():

    from modules.season_utils import get_active_season

    file_path = 'data/dsc_cane_cutting.xlsx'
    season = get_active_season()

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)

        if "Season" in df.columns:
            df = df[df["Season"] == season]

        records = df.to_dict(orient='records')
    else:
        records = []

    return render_template(
        'dsc_cane_cutting_view.html',
        records=records,
        active_season=season
    )

@dsc_bp.route('/cane-cutting/summary')
def dsc_cane_cutting_summary():

    from modules.season_utils import get_active_season
    from modules.reporting_utils import get_reporting_range

    month = int(request.args.get('month', datetime.now().month))
    season = get_active_season()

    summary = {}
    data_rows = []

    try:
        start_date, end_date = get_reporting_range(season, month)

        if not os.path.exists("data/dsc_cane_cutting.xlsx"):
            flash("No data file found.", "warning")
            return render_template("dsc_generic_summary.html",
                                   title="🪓 Cane Cutting Summary",
                                   summary={},
                                   data_rows=[],
                                   active_season=season,
                                   reporting_period={"start": start_date, "end": end_date})

        df = pd.read_excel("data/dsc_cane_cutting.xlsx")

        if "Date" not in df.columns:
            flash("Date column missing in dataset.", "danger")
            return render_template("dsc_generic_summary.html",
                                   title="🪓 Cane Cutting Summary",
                                   summary={},
                                   data_rows=[],
                                   active_season=season,
                                   reporting_period={"start": start_date, "end": end_date})

        df["Date"] = pd.to_datetime(df["Date"])

        # ✅ filter by season first
        if "Season" in df.columns:
            df = df[df["Season"] == season]

        # ✅ then filter by reporting period
        df_filtered = df[
            (df["Date"] >= start_date) &
            (df["Date"] <= end_date)
        ]

        if not df_filtered.empty:

            if 'Field' in df_filtered.columns:
                df_filtered['Field'] = (
                    df_filtered['Field']
                    .astype(str)
                    .str.replace(',', '', regex=False)
                )

            if 'Bundles Cut' in df_filtered.columns:
                summary['Total Bundles Cut'] = int(df_filtered['Bundles Cut'].sum())

            if 'Hectares' in df_filtered.columns:
                summary['Total Hectares'] = round(df_filtered['Hectares'].sum(), 2)

            if 'Field' in df_filtered.columns:
                summary['Fields Worked'] = df_filtered['Field'].nunique()

            labor_columns = [
                'Foreman', 'Capitaos', 'Water Drawers', 'Dippers',
                'Needlemen', 'Bicycle Guards', 'Feeder Breakers',
                'Cane Cutters', 'First-Aider',
                'SHE Representative', 'Tools Keeper'
            ]

            total_labour = 0
            for col in labor_columns:
                if col in df_filtered.columns and pd.api.types.is_numeric_dtype(df_filtered[col]):
                    total_labour += df_filtered[col].sum()

            if total_labour > 0:
                summary['Total Labour (All Roles)'] = int(total_labour)

            data_rows = df_filtered.to_dict(orient='records')

        else:
            flash("⚠️ No records found for this reporting period.", "warning")

    except Exception as e:
        flash(f"Error generating summary: {e}", "danger")
        start_date = end_date = datetime.now()

    return render_template(
        "dsc_generic_summary.html",
        title="🪓 Cane Cutting Summary",
        summary=summary,
        data_rows=data_rows,
        active_season=season,
        selected_month=month,
        reporting_period={"start": start_date, "end": end_date}
    )


def create_excel_if_missing(filename, extra_fields=[]):
    path = f'data/{filename}'
    if not os.path.exists(path):
        columns = ['Date', 'Field', 'Bundles'] + extra_fields
        df = pd.DataFrame(columns=columns)
        df.to_excel(path, index=False)
    # Create all DSC files with basic structure
    create_excel_if_missing("dsc_cane_shifting.xlsx", ["Laborers"])
    create_excel_if_missing("dsc_cane_scraping.xlsx", ["Scrapers"])
    create_excel_if_missing("dsc_seedcane_cutting.xlsx", ["Cutters"])
    create_excel_if_missing("dsc_seedcane_chopping.xlsx", ["Choppers"])
    create_excel_if_missing("dsc_planting.xlsx", ["Planters"])


def handle_dsc_form(file_name, columns, form_title):

    from modules.season_utils import get_active_season

    file_path = f'data/{file_name}'
    season = get_active_season()

    # ✅ Ensure Season column exists
    if "Season" not in columns:
        columns = ["Season"] + columns

    if request.method == 'POST':

        data = {col: request.form.get(col, '') for col in columns}
        data["Season"] = season  # 🔒 Force active season

        # Basic required validation
        required_fields = ["Date", "Field"]
        if "Bundles" in columns:
            required_fields.append("Bundles")

        for field in required_fields:
            if not data.get(field):
                flash(f"{field} is required.", "danger")
                return redirect(request.url)

        try:
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
            else:
                df = pd.DataFrame(columns=columns)

            # Ensure all columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = None

            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_excel(file_path, index=False)

            flash("✅ Record saved successfully", "success")

        except Exception as e:
            flash(f"❌ Error saving record: {e}", "danger")

        return redirect(request.url)

    return render_template(
        'dsc_generic_form.html',
        title=form_title,
        columns=[c for c in columns if c != "Season"],  # hide Season in form
        active_season=season
    )

@dsc_bp.route('/cane-shifting', methods=['GET', 'POST'])
def cane_shifting_form():
    return handle_dsc_form("dsc_cane_shifting.xlsx", ["Date", "Field", "Bundles", "Laborers", "Capitao", "Dipper", "B/Guard", "First_Aider", "SHEQ"], "🚚 Cane Shifting")

@dsc_bp.route('/cane-scraping', methods=['GET', 'POST'])
def cane_scraping_form():
    return handle_dsc_form("dsc_cane_scraping.xlsx", ["Date", "Field", "Bundles", "Scrapers", "Capitao", "Dipper", "B/Guard", "First_Aider", "SHEQ"], "🧹 Cane Scraping")

@dsc_bp.route('/seedcane-cutting', methods=['GET', 'POST'])
def seedcane_cutting_form():
    return handle_dsc_form("dsc_seedcane_cutting.xlsx", ["Date", "Field", "Destination", "Bundles", "Cutters", "Capitao", "Dipper", "Tasker", "N/Man", "B/Guard", "First_Aider", "SHEQ"], "🌱 Seedcane Cutting")

@dsc_bp.route('/seedcane-chopping', methods=['GET', 'POST'])
def seedcane_chopping_form():
    return handle_dsc_form("dsc_seedcane_chopping.xlsx", ["Date", "Field", "Bundles", "Choppers", "Capitao", "Dipper", "B/Guard", "First_Aider", "SHEQ"], "🔪 Seedcane Chopping")

@dsc_bp.route('/planting', methods=['GET', 'POST'])
def planting_form():
    return handle_dsc_form("dsc_planting.xlsx", ["Date", "Field", "Bundles", "Hectares", "Capitao", "Planters", "Gleaners", "Water Drawers", "First-Aid", "SHEQ"], "🌾 Planting")


# === Cane Shifting ===
@dsc_bp.route('/cane-shifting/view')
def cane_shifting_records():
    return render_template('dsc_generic_view.html', title="Cane Shifting Records", records=view_records('dsc_cane_shifting.xlsx'))

@dsc_bp.route('/cane-shifting/summary')
def dsc_cane_shifting_summary():
    return handle_dsc_summary(
        "data/dsc_cane_shifting.xlsx",
        "🚚 Cane Shifting Summary"
    )


# === Cane Scraping ===
@dsc_bp.route('/cane-scraping/view')
def cane_scraping_records():
    return render_template('dsc_generic_view.html', title="Cane Scraping Records", records=view_records('dsc_cane_scraping.xlsx'))



@dsc_bp.route('/cane-scraping/summary')
def dsc_cane_scraping_summary():
    return handle_dsc_summary(
        "data/dsc_cane_scraping.xlsx",
        "🧹 Cane Scraping Summary"
    )



# === Seedcane Cutting ===
@dsc_bp.route('/seedcane-cutting/view')
def seedcane_cutting_records():
    return render_template('dsc_generic_view.html', title="Seedcane Cutting Records", records=view_records('dsc_seedcane_cutting.xlsx'))


@dsc_bp.route('/seedcane-cutting/summary')
def dsc_seedcane_cutting_summary():

    from datetime import datetime
    from flask import request, render_template, flash
    import pandas as pd

    from modules.season_utils import get_active_season
    from modules.reporting_utils import get_reporting_range, load_and_filter

    summary = {}
    data_rows = []

    try:
        month = int(request.args.get('month', datetime.now().month))
        season = get_active_season()

        start_date, end_date = get_reporting_range(season, month)

        df_filtered = load_and_filter(
            "data/dsc_seedcane_cutting.xlsx",
            start_date,
            end_date,
            season=season
        )

        if df_filtered.empty:
            flash("⚠️ No records found for this reporting period.", "warning")
        else:
            data_rows = df_filtered.to_dict(orient='records')

            # === Bundles Summary ===
            if 'Bundles Cut' in df_filtered.columns:
                summary['Total Bundles Cut'] = int(df_filtered['Bundles Cut'].sum())

            # === Field Count ===
            if 'Field' in df_filtered.columns:
                summary['Fields Worked'] = df_filtered['Field'].nunique()

            # === Labour Summary ===
            labor_columns = [
                'Foreman', 'Capitaos', 'Water Drawers', 'Dippers', 'Needlemen',
                'Bicycle Guards', 'Feeder Breakers', 'Cane Cutters',
                'First-Aider', 'SHE Representative', 'Tools Keeper'
            ]

            total_labour = sum(
                df_filtered[col].sum()
                for col in labor_columns
                if col in df_filtered.columns
                and pd.api.types.is_numeric_dtype(df_filtered[col])
            )

            if total_labour > 0:
                summary['Total Labour (All Roles)'] = int(total_labour)

    except Exception as e:
        flash(f"Error generating summary: {e}", "danger")

    return render_template(
        "dsc_generic_summary.html",
        title="🌱 Seedcane Cutting Summary",
        summary=summary,
        data_rows=data_rows,
        active_season=season,
        selected_month=month,
        reporting_period={"start": start_date, "end": start_date} if False else {"start": start_date, "end": end_date}
    )

# === Seedcane Chopping ===
@dsc_bp.route('/seedcane-chopping/view')
def seedcane_chopping_records():
    return render_template('dsc_generic_view.html', title="Seedcane Chopping Records", records=view_records('dsc_seedcane_chopping.xlsx'))


@dsc_bp.route('/seedcane-chopping/summary')
def dsc_seedcane_chopping_summary():
    return handle_dsc_summary("data/dsc_seedcane_chopping.xlsx",
        "🔪 Seedcane Chopping Monthly Summary",

    )

# === Planting ===
@dsc_bp.route('/planting/view')
def planting_records():
    return render_template('dsc_generic_view.html', title="Planting Records", records=view_records('dsc_planting.xlsx'))


@dsc_bp.route('/planting/summary')
def dsc_planting_summary():

    return handle_dsc_summary("data/dsc_planting.xlsx",
        "🌾 Planting Monthly Summary",

    )







from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from datetime import datetime

dsc_bp = Blueprint('dsc', __name__)

import pandas as pd
import os

def view_records(file_name):
    file_path = os.path.join('data', file_name)
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        return df.to_dict(orient='records')
    else:
        return []

from datetime import datetime

def monthly_summary(filename, year=None, month=None):
    file_path = os.path.join('data', filename)
    if not os.path.exists(file_path):
        return {"summary": {}, "grouped": []}

    df = pd.read_excel(file_path)
    if 'Date' not in df or 'Field' not in df:
        return {"summary": {}, "grouped": []}

    df['Date'] = pd.to_datetime(df['Date'])

    now = datetime.now()
    year = int(year) if year else now.year
    month = int(month) if month else now.month

    df = df[(df['Date'].dt.month == month) & (df['Date'].dt.year == year)]

    if df.empty:
        return {"summary": {}, "grouped": []}

    totals = df.select_dtypes(include='number').sum().to_dict()
    grouped = df.groupby('Field').sum(numeric_only=True).reset_index()

    return {"summary": totals, "grouped": grouped.to_dict(orient='records')}


from flask import request, render_template
from datetime import datetime
import pandas as pd
import os
from modules.reporting_utils import get_reporting_range


def load_and_filter(file_path, start_date, end_date):
    if not os.path.exists(file_path):
        return pd.DataFrame()

    df = pd.read_excel(file_path)
    df['Date'] = pd.to_datetime(df['Date'])
    return df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]


def prepare_summary(df, key_column, value_column):
    if df.empty:
        return []
    return df.groupby(key_column).agg({value_column: 'sum'}).reset_index().to_dict(orient="records")


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

    # Allow optional query params for month/year
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    month_name = datetime(year, month, 1).strftime('%B %Y')

    summaries = []
    for act in activities:
        try:
            df = pd.read_excel(f'data/{act["file"]}')
            df['Date'] = pd.to_datetime(df['Date'])
            df_filtered = df[(df['Date'].dt.month == month) & (df['Date'].dt.year == year)]
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

    return render_template("dsc_dashboard.html", summaries=summaries, month_name=month_name,
                           selected_month=month, selected_year=year)

@dsc_bp.route('/cane-cutting', methods=['GET', 'POST'])
def cane_cutting_form():
    file_path = 'data/dsc_cane_cutting.xlsx'
    columns = [
        'Date', 'Field', 'Bundles Cut',
        'Foreman', 'Capitaos', 'Water Drawers', 'Dippers',
        'Needlemen', 'Bicycle Guards', 'Feeder Breakers',
        'Cane Cutters', 'First-Aider', 'SHE Representative', 'Tools Keeper'
    ]

    if request.method == 'POST':
        data = {col: request.form.get(col, '') for col in columns}

        if not data['Date'] or not data['Field'] or not data['Bundles Cut']:
            flash("Date, Field, and Bundles Cut are required.", "danger")
            return redirect(url_for('dsc.cane_cutting_form'))

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
        else:
            df = pd.DataFrame(columns=columns)

        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_excel(file_path, index=False)
        flash("✅ Cane Cutting record saved.", "success")
        return redirect(url_for('dsc.cane_cutting_form'))

    return render_template('dsc_cane_cutting_form.html', columns=columns)


@dsc_bp.route('/cane-cutting/view')
def dsc_cane_cutting_records():
    file_path = 'data/dsc_cane_cutting.xlsx'

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        records = df.to_dict(orient='records')
    else:
        records = []

    return render_template('dsc_cane_cutting_view.html', records=records)


@dsc_bp.route('/cane-cutting/summary')
def dsc_cane_cutting_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_cane_cutting.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Bundles Cut")

    return render_template("dsc_generic_summary.html",
        title="🪓 Cane Cutting Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
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
    file_path = f'data/{file_name}'

    if request.method == 'POST':
        data = {col: request.form.get(col, '') for col in columns}
        if not data['Date'] or not data['Field'] or not data['Bundles']:
            flash("Date, Field, and Bundles are required.", "danger")
            return redirect(request.url)

        df = pd.read_excel(file_path) if os.path.exists(file_path) else pd.DataFrame(columns=columns)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_excel(file_path, index=False)
        flash("✅ Record saved", "success")
        return redirect(request.url)

    return render_template('dsc_generic_form.html', title=form_title, columns=columns)

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
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_cane_shifting.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Bundles")

    return render_template("dsc_generic_summary.html",
        title="🚚 Cane Shifting Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
        reporting_period={"start": start_date, "end": end_date}
    )

# === Cane Scraping ===
@dsc_bp.route('/cane-scraping/view')
def cane_scraping_records():
    return render_template('dsc_generic_view.html', title="Cane Scraping Records", records=view_records('dsc_cane_scraping.xlsx'))


@dsc_bp.route('/cane-scraping/summary')
def dsc_cane_scraping_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_cane_scraping.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Bundles")

    return render_template("dsc_generic_summary.html",
        title="🧹 Cane Scraping Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
        reporting_period={"start": start_date, "end": end_date}
    )


# === Seedcane Cutting ===
@dsc_bp.route('/seedcane-cutting/view')
def seedcane_cutting_records():
    return render_template('dsc_generic_view.html', title="Seedcane Cutting Records", records=view_records('dsc_seedcane_cutting.xlsx'))


@dsc_bp.route('/seedcane-cutting/summary')
def dsc_seedcane_cutting_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_seedcane_cutting.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Bundles")

    return render_template("dsc_generic_summary.html",
        title="🌱 Seedcane Cutting Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
        reporting_period={"start": start_date, "end": end_date}
    )


# === Seedcane Chopping ===
@dsc_bp.route('/seedcane-chopping/view')
def seedcane_chopping_records():
    return render_template('dsc_generic_view.html', title="Seedcane Chopping Records", records=view_records('dsc_seedcane_chopping.xlsx'))


@dsc_bp.route('/seedcane-chopping/summary')
def dsc_seedcane_chopping_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_seedcane_chopping.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Bundles")

    return render_template("dsc_generic_summary.html",
        title="🔪 Seedcane Chopping Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
        reporting_period={"start": start_date, "end": end_date}
    )

# === Planting ===
@dsc_bp.route('/planting/view')
def planting_records():
    return render_template('dsc_generic_view.html', title="Planting Records", records=view_records('dsc_planting.xlsx'))


@dsc_bp.route('/planting/summary')
def dsc_planting_summary():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    start_date, end_date = get_reporting_range(month)
    df_filtered = load_and_filter("data/dsc_planting.xlsx", start_date, end_date)
    summary = prepare_summary(df_filtered, "Field", "Hectares")

    return render_template("dsc_generic_summary.html",
        title="🌾 Planting Monthly Summary",
        summary=summary,
        selected_year=year,
        selected_month=month,
        current_year=datetime.now().year,
        month_name=f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
        reporting_period={"start": start_date, "end": end_date}
    )







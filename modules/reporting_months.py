import os
import pandas as pd
from flask import flash, redirect, render_template, request, url_for, Blueprint
from datetime import datetime

reporting_bp = Blueprint('reporting', __name__)

DATA_FILE = 'data/reporting_months.xlsx'

DEFAULT_MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

# ---------------- HELPERS ----------------
def parse_season_year(season: str):
    """
    Returns start_year, end_year as integers from season string
    Supports formats:
      - '2025-2026'
      - '2020/21'
    """
    season = season.strip()
    if "-" in season:
        parts = season.split("-")
        start_year = int(parts[0])
        end_year = int(parts[1])
    elif "/" in season:
        parts = season.split("/")
        start_year = int(parts[0])
        # handle short year like '20/21' → 2021
        end_year = int(str(start_year)[:2] + parts[1])
    else:
        start_year = int(season)
        end_year = start_year
    return start_year, end_year

def get_active_season():
    season_file = os.path.join("data", "active_season.txt")
    if os.path.exists(season_file):
        return open(season_file).read().strip()
    return None

# ---------------- ROUTE ----------------
@reporting_bp.route('/reporting-months', methods=['GET', 'POST'])
def manage_reporting_months():

    season = get_active_season()

    if not season:
        flash("⚠️ No active season found.")
        return redirect(url_for("mill.mill_return_form"))

    # ---------- CREATE FILE IF NOT EXISTS ----------
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Season", "Month", "Start Date", "End Date"])
        df.to_excel(DATA_FILE, index=False)

    df = pd.read_excel(DATA_FILE)
    df.columns = df.columns.str.strip()

    # ---------- FILTER FOR ACTIVE SEASON ----------
    season_df = df[df["Season"] == season] if not df.empty and "Season" in df.columns else pd.DataFrame()

    # ---------- IF SEASON DOES NOT EXIST, AUTO-CREATE DEFAULT STRUCTURE ----------
    if season_df.empty:
        start_year, end_year = parse_season_year(season)

        default_start_dates = []
        default_end_dates = []

        # Example structure: 27th to 26th cycle starting from March
        current_year = start_year
        current_month = 3  # Adjust as needed for your crop season

        for i in range(12):
            start_date = datetime(current_year, current_month, 27)
            if current_month == 12:
                end_date = datetime(current_year + 1, 1, 26)
                next_month = 1
                current_year += 1
            else:
                end_date = datetime(current_year, current_month + 1, 26)
                next_month = current_month + 1

            default_start_dates.append(start_date.strftime("%Y-%m-%d"))
            default_end_dates.append(end_date.strftime("%Y-%m-%d"))

            current_month = next_month

        season_df = pd.DataFrame({
            "Season": season,
            "Month": DEFAULT_MONTHS,
            "Start Date": default_start_dates,
            "End Date": default_end_dates
        })

        df = pd.concat([df, season_df], ignore_index=True)
        df.to_excel(DATA_FILE, index=False)

    # ---------- HANDLE POST UPDATE ----------
    if request.method == 'POST':

        for index in range(len(season_df)):
            start_date = request.form.get(f'start_date_{index}')
            end_date = request.form.get(f'end_date_{index}')

            df.loc[
                (df["Season"] == season) & (df["Month"] == season_df.iloc[index]["Month"]),
                "Start Date"
            ] = start_date

            df.loc[
                (df["Season"] == season) & (df["Month"] == season_df.iloc[index]["Month"]),
                "End Date"
            ] = end_date

        df.to_excel(DATA_FILE, index=False)
        flash(f"✅ Reporting month ranges updated for Season {season}")
        return redirect(url_for('reporting.manage_reporting_months'))

    # ---------- FORMAT FOR HTML ----------
    season_df["Start Date"] = pd.to_datetime(season_df["Start Date"]).dt.strftime('%Y-%m-%d')
    season_df["End Date"] = pd.to_datetime(season_df["End Date"]).dt.strftime('%Y-%m-%d')

    return render_template(
        'reporting_months_form.html',
        months=season_df.to_dict(orient='records'),
        season=season
    )
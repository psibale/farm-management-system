from flask import Blueprint, render_template, request, flash
import pandas as pd
import os
import calendar


mill_bp = Blueprint(
    'mill_bp',
    __name__,
    template_folder='../templates'
)


# ---------------- FILE PATHS ----------------

YIELD_FILE = os.path.join('data', 'yield_data.xlsx')

CALENDAR_FILE = os.path.join('data', 'mill_reporting_months.xlsx')

SEASON_FILE = os.path.join('data', 'season_data.xlsx')
ACTIVE_SEASON_FILE = os.path.join('data', 'active_season.txt')

# ============================================================
#  ✅ Get operating season from active_season.txt
# ============================================================


def get_operating_season():

    # If active season exists, use it
    if os.path.exists(ACTIVE_SEASON_FILE):

        with open(ACTIVE_SEASON_FILE, 'r') as f:
            season = f.read().strip()

        if season:
            return season

    # Otherwise use latest season from season_data.xlsx
    if not os.path.exists(SEASON_FILE):
        return "2025/26"

    df = pd.read_excel(SEASON_FILE)

    df['Start Date'] = pd.to_datetime(df['Start Date'])

    latest = df.sort_values('Start Date').iloc[-1]

    season = latest['Season Name']

    # Save it
    with open(ACTIVE_SEASON_FILE, 'w') as f:
        f.write(season)

    return season

# ============================================================
# GET MILL REPORTING DATE RANGE
# ============================================================

def get_mill_reporting_range(season, month_number):
    """
    Returns Start Date and End Date from mill_reporting_months.xlsx
    based on Season and Month number (1–12)
    """

    if not os.path.exists(CALENDAR_FILE):

        raise ValueError(
            "mill_reporting_months.xlsx not found in data folder"
        )


    df = pd.read_excel(CALENDAR_FILE)

    df.columns = df.columns.str.strip()


    required_cols = [
        'Season',
        'Month',
        'Start Date',
        'End Date'
    ]


    for col in required_cols:

        if col not in df.columns:

            raise ValueError(
                f"Missing column '{col}' in mill_reporting_months.xlsx"
            )


    df['Season'] = df['Season'].astype(str)

    df['Month'] = df['Month'].astype(int)


    filtered = df[
        (df['Season'] == season) &
        (df['Month'] == month_number)
    ]


    if filtered.empty:

        raise ValueError(
            f"No reporting period found for Season {season} Month {month_number}"
        )


    row = filtered.iloc[0]


    start_date = pd.to_datetime(row['Start Date'])

    end_date = pd.to_datetime(row['End Date'])


    return start_date, end_date


# ============================================================
# MILL MONTHLY SUMMARY ROUTE
# ============================================================

@mill_bp.route('/monthly-summary')
def mill_monthly_summary():

    try:

        # ---------------- GET ACTIVE SEASON ----------------

        season = get_operating_season()


        # ---------------- GET MONTH ----------------

        month = int(
            request.args.get('month', 1)
        )


        # ---------------- GET REPORTING RANGE ----------------

        start_date, end_date = get_mill_reporting_range(
            season,
            month
        )


        # ---------------- LOAD YIELD DATA ----------------

        if not os.path.exists(YIELD_FILE):

            raise ValueError(
                "yield_data.xlsx not found in data folder"
            )


        df = pd.read_excel(YIELD_FILE)

        df.columns = df.columns.str.strip()


        required_cols = [
            'Date',
            'Field',
            'Bundles',
            'Yield (Tons)'
        ]


        for col in required_cols:

            if col not in df.columns:

                raise ValueError(
                    f"Missing column '{col}' in yield_data.xlsx"
                )


        df['Date'] = pd.to_datetime(df['Date'])


        # ---------------- FILTER DATA ----------------

        df_filtered = df[

            (df['Date'] >= start_date) &
            (df['Date'] <= end_date)

        ]


        if df_filtered.empty:

            flash(
                f"No yield data found for Season {season} Month {month}",
                "warning"
            )

            return render_template(
                'mill_monthly_summary.html',
                season=season,
                current_month=month
            )


        # ---------------- CREATE SUMMARY ----------------

        summary = df_filtered.groupby(
            'Field',
            as_index=False
        ).agg({

            'Bundles': 'sum',

            'Yield (Tons)': 'sum'

        })


        summary['Average Weight (T/B)'] = (

            summary['Yield (Tons)'] /

            summary['Bundles']

        ).round(3)


        # ---------------- TOTALS ----------------

        total_bundles = summary['Bundles'].sum()

        total_tons = summary['Yield (Tons)'].sum()


        avg_weight = 0

        if total_bundles > 0:

            avg_weight = round(
                total_tons / total_bundles,
                3
            )


        totals = {

            'Bundles': total_bundles,

            'Yield (Tons)': total_tons,

            'Average Weight (T/B)': avg_weight

        }


        # ---------------- MONTH NAME ----------------

        mill_month_names = [

            "Apr", "May", "Jun", "Jul",
            "Aug", "Sep", "Oct", "Nov",
            "Dec", "Jan", "Feb", "Mar"

        ]


        month_name = mill_month_names[month - 1]


        # ---------------- RENDER ----------------

        return render_template(

            'mill_monthly_summary.html',

            title="Mill Monthly Report",

            summary=summary.to_dict(orient='records'),

            totals=totals,

            season=season,

            current_month=month,

            month_name=month_name,

            start_date=start_date.date(),

            end_date=end_date.date()

        )


    except Exception as e:

        flash(str(e), "danger")

        return render_template(

            'mill_monthly_summary.html',

            title="Mill Monthly Report"

        )
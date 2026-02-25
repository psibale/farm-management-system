from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os

mill_months_bp = Blueprint('mill_months_bp', __name__, template_folder='../templates')

FILE_PATH = os.path.join('data', 'mill_reporting_months.xlsx')
SEASON_FILE = os.path.join('data', 'season_data.xlsx')
ACTIVE_SEASON_FILE = os.path.join('data', 'active_season.txt')


# ✅ Get operating season from active_season.txt
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


# ✅ Route
@mill_months_bp.route('/mill-reporting-months', methods=['GET', 'POST'])
def mill_reporting_months():

    season = get_operating_season()

    # ✅ Create file if missing
    if not os.path.exists(FILE_PATH):

        df = pd.DataFrame({
            'Season': [season] * 12,
            'Month': list(range(1, 13)),
            'Start Date': [''] * 12,
            'End Date': [''] * 12
        })

        df.to_excel(FILE_PATH, index=False)

    df = pd.read_excel(FILE_PATH)

    # ✅ Ensure Season column exists
    if 'Season' not in df.columns:

        df['Season'] = season
        df.to_excel(FILE_PATH, index=False)

    # ✅ Ensure season exists
    df_season = df[df['Season'] == season]

    if df_season.empty:

        new_df = pd.DataFrame({
            'Season': [season] * 12,
            'Month': list(range(1, 13)),
            'Start Date': [''] * 12,
            'End Date': [''] * 12
        })

        df = pd.concat([df, new_df], ignore_index=True)
        df.to_excel(FILE_PATH, index=False)

        df_season = new_df


    # ✅ SAVE ENTIRE DOCUMENT (not per row)
    if request.method == 'POST':

        try:

            for i in range(1, 13):

                start_date = request.form.get(f'start_date_{i}')
                end_date = request.form.get(f'end_date_{i}')

                df.loc[
                    (df['Season'] == season) &
                    (df['Month'] == i),
                    ['Start Date', 'End Date']
                ] = [start_date, end_date]

            df.to_excel(FILE_PATH, index=False)

            flash(f"Mill Calendar saved successfully for Season {season}", "success")

            return redirect(url_for('mill_months_bp.mill_reporting_months'))

        except Exception as e:

            flash(f"Error saving file: {e}", "danger")


    # Sort months
    df_season = df[df['Season'] == season].sort_values('Month')

    # Get all seasons from master file
    if os.path.exists(SEASON_FILE):

        df_seasons = pd.read_excel(SEASON_FILE)
        seasons = df_seasons['Season Name'].tolist()

    else:
        seasons = [season]


    return render_template(
        'mill_reporting_months_form.html',
        title="Mill Reporting Months",
        months=df_season.to_dict(orient='records'),
        season=season,
        seasons=seasons
    )
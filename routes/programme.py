from flask import Blueprint, render_template
import pandas as pd
from datetime import datetime
from modules.season import get_active_season
from modules.programmes import get_weekly_programme_for_stage as get_programme_for_stage

programme = Blueprint('programme', __name__)

@programme.route('/programme_schedule')
def programme_schedule():
    # Get current season
    current_season = get_active_season()

    # Load and filter planting records
    planting_df = pd.read_excel('data/planting_records.xlsx')
    planting_df['Date'] = pd.to_datetime(planting_df['Date'], errors='coerce')
    if 'Season' in planting_df.columns:
        planting_df = planting_df[planting_df['Season'] == current_season]
    latest_planting = planting_df.sort_values('Date').groupby('Field').last().reset_index()
    latest_planting['CropStartDate'] = latest_planting['Date']

    # Load and filter harvesting records
    harvesting_df = pd.read_excel('data/harvesting_records.xlsx')
    harvesting_df['Date'] = pd.to_datetime(harvesting_df['Date'], errors='coerce')
    if 'Season' in harvesting_df.columns:
        harvesting_df = harvesting_df[harvesting_df['Season'] == current_season]
    latest_harvesting = harvesting_df.sort_values('Date').groupby('Field').last().reset_index()
    latest_harvesting['CropStartDate'] = latest_harvesting['Date']

    # Combine planting and harvesting records (prefer planting if exists)
    combined_df = pd.merge(
        latest_harvesting[['Field', 'CropStartDate']],
        latest_planting[['Field', 'CropStartDate']],
        on='Field',
        how='outer',
        suffixes=('_harvest', '_plant')
    )
    combined_df['CropStartDate'] = combined_df['CropStartDate_plant'].combine_first(combined_df['CropStartDate_harvest'])
    combined_df = combined_df[['Field', 'CropStartDate']].dropna()

    # Compute crop age and determine programme stage
    combined_df['CropAgeDays'] = (datetime.today() - combined_df['CropStartDate']).dt.days
    combined_df['CropStage'] = combined_df['CropAgeDays'].apply(get_programme_for_stage)

    # Ensure CropStage is string before grouping
    combined_df['CropStage'] = combined_df['CropStage'].astype(str)

    # Group by activity
    programme_by_activity = combined_df.groupby('CropStage')['Field'].apply(list).to_dict()

    return render_template('programme_schedule.html',
                           activity_dict=programme_by_activity,
                           current_season=current_season)

from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from modules.utils import role_required

season_bp = Blueprint('season', __name__, url_prefix='/season')

SEASON_FILE = 'data/season_data.xlsx'
ACTIVE_SEASON_FILE = 'data/active_season.txt'

# Ensure storage files exist
os.makedirs('data', exist_ok=True)
if not os.path.exists(SEASON_FILE):
    pd.DataFrame(columns=["Season Name", "Start Date", "End Date"]).to_excel(SEASON_FILE, index=False)
if not os.path.exists(ACTIVE_SEASON_FILE):
    with open(ACTIVE_SEASON_FILE, 'w') as f:
        f.write("")

# Helper functions
def load_seasons():
    return pd.read_excel(SEASON_FILE)

def get_active_season():
    try:
        with open(ACTIVE_SEASON_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def set_active_season(season_name):
    with open(ACTIVE_SEASON_FILE, 'w') as f:
        f.write(season_name)

# Routes
@season_bp.route('/', methods=['GET'])
@role_required(["Admin"])
def manage_season():
    df = load_seasons()
    seasons = df.to_dict(orient='records')
    all_seasons = df["Season Name"].dropna().unique().tolist()
    current = get_active_season()
    return render_template('season/manage_season.html',
                           seasons=seasons,
                           all_seasons=all_seasons,
                           current_season=current)

@season_bp.route('/add', methods=['POST'])
@role_required(["Admin"])
def add_season():
    season = request.form.get('season_name')
    start = request.form.get('start_date')
    end = request.form.get('end_date')

    if not season or not start or not end:
        flash("All fields are required", "danger")
        return redirect(url_for('season.manage_season'))

    df = load_seasons()
    new_row = pd.DataFrame([[season, start, end]], columns=["Season Name", "Start Date", "End Date"])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(SEASON_FILE, index=False)

    flash(f"Season '{season}' added successfully.", "success")
    return redirect(url_for('season.manage_season'))

@season_bp.route('/set_active', methods=['POST'])
@role_required(["Admin"])
def set_active_season_route():
    selected = request.form.get('active_season')
    if selected:
        set_active_season(selected)
        flash(f"Active season set to '{selected}'", "success")
    else:
        flash("Please select a season.", "warning")
    return redirect(url_for('season.manage_season'))

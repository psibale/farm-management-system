from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import json
import bcrypt
import pandas as pd
from datetime import datetime
from modules.utils import role_required
from modules.alerts import get_all_alerts
from modules.agriculture import agriculture_bp
from modules.farm_activities import farm_activities_bp
from modules.activities import activity_bp
from modules.hr import hr_bp
from modules.user_mgmt import user_bp
from modules.expense_budget import expense_bp
from modules.alerts import alerts_bp
from modules.season import season_bp
from modules.weather import weather_bp
from modules.gis import gis_bp
from modules.recalculate import recalc_bp
from modules.inventory import inventory_bp
from modules.backup import backup_bp
from modules.dsc import dsc_bp
from modules.mill_return import mill_bp
from modules.reporting_months import reporting_bp

# --- App Setup ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- Config ---
USER_FILE = "users.json"
LOG_FILE = "user_log.txt"
YIELD_FILE = "data/yield_data.xlsx"
FIELD_FILE = "data/registered_fields.xlsx"
MAX_ATTEMPTS = 3
failed_attempts = {}

# --- Helper Functions ---
def load_users():
    if os.path.exists("users.xlsx"):
        df = pd.read_excel("users.xlsx")
        users = {}
        for _, row in df.iterrows():
            users[row["Username"]] = {
                "password": row["Password"],
                "role": row["Role"]
            }
        return users
    return {}

def log_activity(username, action):
    with open(LOG_FILE, "a") as file:
        file.write(f"{datetime.now()} - {username} {action}\n")

def get_active_season():
    try:
        with open("data/active_season.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "2024/25"

def get_available_seasons():
    try:
        df = pd.read_excel(YIELD_FILE)
        return sorted(df['Season'].dropna().unique(), reverse=True)
    except:
        return ["2024/25"]

def get_summary_data(df):
    total_fields = df['Field'].nunique()
    total_yield = df['Yield (Tons)'].sum()
    avg_yield_per_field = total_yield / total_fields if total_fields else 0

    yield_per_ha = 0
    if os.path.exists(FIELD_FILE):
        reg_df = pd.read_excel(FIELD_FILE)
        merged = pd.merge(df, reg_df, on="Field", how="left")

        # Filter harvested fields only
        harvested = merged[(merged['Yield (Tons)'] > 0) & (merged['Hectares'].notna()) & (merged['Hectares'] > 0)]
        if not harvested.empty:
            harvested['Yield per Ha'] = harvested['Yield (Tons)'] / harvested['Hectares']
            yield_per_ha = harvested['Yield per Ha'].mean()

    return {
        'total_fields': total_fields,
        'total_yield': round(total_yield, 2),
        'avg_yield_per_field': round(avg_yield_per_field, 2),
        'yield_per_ha': round(yield_per_ha, 2)
    }

def get_field_yield_data(df):
    grouped = df.groupby('Field')['Yield (Tons)'].sum().reset_index()
    grouped = grouped.sort_values(by="Yield (Tons)", ascending=False)
    return grouped.to_dict(orient="records")

def get_prefix_grouped_yield_data(df):
    df = df.copy()
    df['Prefix'] = df['Field'].str[:2]
    grouped = df.groupby('Prefix')['Yield (Tons)'].sum().reset_index()
    return grouped.to_dict(orient="records")

# --- Auth Routes ---
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    users = load_users()

    if username in failed_attempts and failed_attempts[username] >= MAX_ATTEMPTS:
        flash("Too many failed attempts! Please reset your password.", "danger")
        return redirect(url_for('home'))

    if username in users:
        stored_hashed_password = users[username]["password"]
        if bcrypt.checkpw(password.encode(), stored_hashed_password.encode()):
            session['username'] = username
            session['role'] = users[username]["role"]
            failed_attempts[username] = 0
            log_activity(username, "logged in")
            return redirect(url_for('dashboard'))
        else:
            failed_attempts[username] = failed_attempts.get(username, 0) + 1
            log_activity(username, "failed login")

    flash("Invalid username or password!", "danger")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    username = session.get('username', '')
    session.clear()
    log_activity(username, "logged out")
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))

    selected_season = request.args.get("season")
    all_seasons = get_available_seasons()
    season = selected_season if selected_season else get_active_season()

    try:
        df = pd.read_excel(YIELD_FILE)
        season_df = df[df['Season'] == season]
    except:
        season_df = pd.DataFrame(columns=["Field", "Yield (Tons)", "Season"])

    summary = get_summary_data(season_df)
    field_yields = get_field_yield_data(season_df)
    prefix_grouped_yields = get_prefix_grouped_yield_data(season_df)

    equipment_alerts, inventory_alerts, budget_alerts, retirement_alerts = get_all_alerts()
    alert_count = len(equipment_alerts) + len(inventory_alerts) + len(budget_alerts) + len(retirement_alerts)

    return render_template("dashboard.html",
                           username=session['username'],
                           role=session['role'],
                           season=season,
                           all_seasons=all_seasons,
                           summary=summary,
                           field_yields=field_yields,
                           prefix_grouped_yields=prefix_grouped_yields,
                           alert_count=alert_count,
                           equipment_alerts=equipment_alerts,
                           inventory_alerts=inventory_alerts,
                           budget_alerts=budget_alerts,
                           retirement_alerts=retirement_alerts)

# --- Dummy Routes ---
@app.route('/inventory')
def inventory():
    return '<h2>Inventory Section</h2>'

@app.route('/gis')
def gis_home():
    return render_template('gis_home.html')

@app.route('/budget')
def budget_tracking():
    return "Expense & Budget Tracking Page - Under Construction"

@app.route('/weather')
def weather_entry():
    return "Weather Data Entry Page - Under Construction"

@app.route('/dash')
def dash():
    return "Dashboard Analytics Page - Under Construction"

@app.route('/backup', methods=['POST'])
def backup_to_drive():
    flash("Backup to Google Drive started (mock)", "info")
    return redirect(url_for('dashboard'))

@app.route('/dsc')
def dsc_dashboard():
    return render_template("dsc_dashboard.html", summaries=[])

@app.route('/dsc/submission-log')
def dsc_submission_log():
    return "<h3>DSC Submission Log Page (Coming Soon)</h3>"

# --- Register Blueprints ---
app.register_blueprint(agriculture_bp, url_prefix="/agriculture")
app.register_blueprint(farm_activities_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(hr_bp)
app.register_blueprint(user_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(season_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(gis_bp)
app.register_blueprint(recalc_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(dsc_bp, url_prefix='/dsc')
app.register_blueprint(mill_bp)
app.register_blueprint(reporting_bp, url_prefix='/reporting')

# --- Background Scheduler for Backup ---
from apscheduler.schedulers.background import BackgroundScheduler
from drive_backup import backup_files_to_drive

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(backup_files_to_drive, 'cron', hour=19, minute=0)  # Daily at 7 PM
    scheduler.start()

start_scheduler()

# --- Run ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

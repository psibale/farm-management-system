from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import bcrypt
import pandas as pd
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
# Import your get_all_alerts function from alerts.py
from modules.alerts import get_all_alerts

# -----------------------------
# ESTATE MAPPING FUNCTION
# -----------------------------
def classify_estate(field_code):
    """Returns estate name based on field prefix."""
    if not isinstance(field_code, str):
        return "Other"

    code = field_code.strip().upper()

    if code.startswith("DG"):
        return "Main Estate"
    elif code.startswith("L"):
        return "Liwaladzi Estate"
    elif code.startswith("M"):
        return "Kasitu Estate"

    return "Other"


# -----------------------------
# DASHBOARD ROUTE
# -----------------------------
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))

    # --- Season selection ---
    selected_season = request.args.get("season")
    all_seasons = get_available_seasons()
    season = selected_season if selected_season else get_active_season()

    # --- Load yield data for season ---
    try:
        df = pd.read_excel(YIELD_FILE)
        season_df = df[df['Season'] == season]
    except Exception as e:
        print(f"Error reading yield file: {e}")
        season_df = pd.DataFrame(columns=["Field", "Yield (Tons)", "Season"])

    # --- Compute field-level yields ---
    field_yields = season_df[["Field", "Yield (Tons)"]].to_dict(orient="records")

    # -----------------------------
    #  1) Compute Estate for Each Field
    # -----------------------------
    def classify_estate(field):
        try:
            f = str(field).strip().upper()
            if f.startswith("DG"):
                return "Main Estate"
            elif f.startswith("L"):
                return "Liwaladzi Estate"
            elif f.startswith("M"):
                return "Kasitu Estate"
            else:
                return "Other"
        except:
            return "Other"

    season_df["Estate"] = season_df["Field"].apply(classify_estate)

    # -----------------------------
    #  2) Compute Yield per Estate
    # -----------------------------
    estate_yield = (
        season_df.groupby("Estate")["Yield (Tons)"]
        .sum()
        .round(2)
        .to_dict()
    )

    # -----------------------------
    # 3) Compute Average TCH per Estate (Corrected)
    # -----------------------------
    try:
        harvest_df = pd.read_excel("data/harvesting_records.xlsx")
    except Exception as e:
        print(f"Error reading harvesting records: {e}")
        harvest_df = pd.DataFrame(columns=["Field", "Harvested Area (ha)"])

    # Detect which column holds harvested area
    if "Harvested Area (ha)" in harvest_df.columns:
        area_col = "Harvested Area (ha)"
    elif "Area" in harvest_df.columns:
        area_col = "Area"
    else:
        raise Exception("harvesting_records.xlsx must contain 'Harvested Area (ha)' or 'Area' column")

    # 1️⃣ Sum harvested area per Field
    area_per_field = (
        harvest_df.groupby("Field")[area_col]
        .sum()
        .reset_index()
        .rename(columns={area_col: "Total_Area"})
    )

    # 2️⃣ Merge with yield data (season_df)
    df_merged = season_df.merge(area_per_field, on="Field", how="left")

    # 3️⃣ Calculate TCH per field
    df_merged["TCH"] = df_merged["Yield (Tons)"] / df_merged["Total_Area"]

    # 4️⃣ Calculate Estate-level average TCH
    estate_tch = (
        df_merged.groupby("Estate")["TCH"]
        .mean()
        .round(2)
        .to_dict()
    )

    # -----------------------------
    #  4) Build Estate Summary Object
    # -----------------------------
    estate_summary = {}
    for estate in estate_yield.keys():
        estate_summary[estate] = {
            "total_yield": round(estate_yield.get(estate, 0), 2),
            "avg_tch": round(estate_tch.get(estate, 0), 2),
        }

    # -----------------------------
    #  5) General Dashboard Cards (Season-specific)
    # -----------------------------
    total_fields = season_df["Field"].nunique()
    total_yield = round(season_df["Yield (Tons)"].sum(), 2)
    avg_yield_per_field = round(total_yield / total_fields, 2) if total_fields > 0 else 0

    # Merge season_df with field_area for total area
    df_area = season_df.merge(area_per_field, on="Field", how="left")
    total_area = df_area["Total_Area"].sum()
    yield_per_ha = round(total_yield / total_area, 2) if total_area > 0 else 0

    # -----------------------------
    #  6) Render template
    # -----------------------------
    return render_template(
        "dashboard.html",
        season=season,
        all_seasons=all_seasons,         # season dropdown
        total_fields=total_fields,
        total_yield=total_yield,
        avg_yield_per_field=avg_yield_per_field,
        yield_per_ha=yield_per_ha,
        estate_summary=estate_summary,
        estate_yield=estate_yield,       # pie chart
        field_yields=field_yields        # field-level bar chart
    )


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

from routes.programme import programme
app.register_blueprint(programme)

# app.py (or __init__.py)

from datetime import datetime, timedelta

# ✅ Register a robust Jinja filter for strftime
@app.template_filter("strftime")
def _jinja2_filter_datetime(value, fmt="%Y-%m-%d"):
    if value is None or value == "":
        return ""

    # Case 1: Already a datetime
    if isinstance(value, datetime):
        return value.strftime(fmt)

    # Case 2: Excel serial number (int/float)
    if isinstance(value, (int, float)):
        # Excel's "day 1" = 1899-12-30
        excel_epoch = datetime(1899, 12, 30)
        try:
            date = excel_epoch + timedelta(days=int(value))
            return date.strftime(fmt)
        except Exception:
            return str(value)

    # Case 3: String (try parsing ISO first)
    if isinstance(value, str):
        try:
            date = datetime.fromisoformat(value)
            return date.strftime(fmt)
        except Exception:
            return value  # fallback: return as-is

    # Fallback
    return str(value)

from routes.harvest_routes import harvest_bp
app.register_blueprint(harvest_bp)

from modules.ai_routes import ai_bp
app.register_blueprint(ai_bp)

from modules.mill_reporting_months import mill_months_bp
app.register_blueprint(mill_months_bp)

from modules.mill_reports_dashboard import mill_reports_bp
app.register_blueprint(mill_reports_bp)

from modules.mill_monthly_summary import mill_bp
app.register_blueprint(mill_bp)

# --- Run ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import json
import bcrypt
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

USER_FILE = "users.json"
LOG_FILE = "user_log.txt"
MAX_ATTEMPTS = 3
failed_attempts = {}
YIELD_FILE = "data/yield_data.xlsx"
FIELD_FILE = "data/registered_fields.xlsx"


# -------------------- USER MANAGEMENT --------------------

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as file:
        return json.load(file)


def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent=4)


def log_activity(username, action):
    with open(LOG_FILE, "a") as file:
        file.write(f"{datetime.now()} - {username} {action}\n")


# -------------------- SEASON HELPERS --------------------

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


# -------------------- SUMMARY & ANALYTICS --------------------

def get_summary_data(df):
    """Safely compute main KPI cards on dashboard."""

    if df.empty:
        return {
            'Total Fields': 0,
            'Total Yield (Tons)': 0,
            'Avg Yield/Field': 0,
            'Avg Yield/Ha': 0
        }

    total_fields = df['Field'].nunique() if 'Field' in df.columns else 0
    total_yield = df['Yield (Tons)'].sum()
    avg_yield_per_field = total_yield / total_fields if total_fields else 0

    # --- Yield per Hectare (weighted) ---
    avg_yield_ha = 0

    if os.path.exists(FIELD_FILE):
        try:
            fields_df = pd.read_excel(FIELD_FILE)

            if 'Field' in fields_df.columns and 'Hectares' in fields_df.columns:

                merged = pd.merge(df, fields_df, on="Field", how="left")

                merged = merged[merged['Hectares'].fillna(0) > 0]

                if not merged.empty:
                    merged['Yield/Ha'] = merged['Yield (Tons)'] / merged['Hectares']

                    # Weighted average = sum(y/ha * ha) / total ha
                    avg_yield_ha = (
                        (merged['Yield/Ha'] * merged['Hectares']).sum()
                        / merged['Hectares'].sum()
                    )
        except Exception as e:
            print("Yield/Ha Error:", e)

    return {
        'Total Fields': total_fields,
        'Total Yield (Tons)': round(total_yield, 2),
        'Avg Yield/Field': round(avg_yield_per_field, 2),
        'Avg Yield/Ha': round(avg_yield_ha, 2)
    }


def get_field_yield_data(df):
    if df.empty:
        return []
    grouped = df.groupby('Field')['Yield (Tons)'].sum().reset_index()
    return grouped.sort_values(by="Yield (Tons)", ascending=False).to_dict(orient="records")


def get_prefix_grouped_yield_data(df):
    if df.empty:
        return []
    df['Prefix'] = df['Field'].str[:2]
    grouped = df.groupby('Prefix')['Yield (Tons)'].sum().reset_index()
    return grouped.to_dict(orient="records")


# -------------------- ESTATE MAPPING --------------------

def map_estate(field):
    if isinstance(field, str):
        if field.startswith("DG"):
            return "Main Estate"
        elif field.startswith("L"):
            return "Liwaladzi Estate"
        elif field.startswith("M"):
            return "Kasitu Estate"
    return "Other"


# -------------------- ROUTES --------------------

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
        stored_hashed = users[username]["password"]
        if bcrypt.checkpw(password.encode(), stored_hashed.encode()):
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

    # --- Yield by Estate ---
    if "Field" in season_df.columns:
        season_df["Estate"] = season_df["Field"].apply(map_estate)
        yield_by_estate = (
            season_df.groupby("Estate")["Yield (Tons)"]
            .sum()
            .reset_index()
            .to_dict(orient="records")
        )
    else:
        yield_by_estate = []

    return render_template(
        "dashboard.html",
        username=session['username'],
        role=session['role'],
        season=season,
        all_seasons=all_seasons,
        summary=summary,
        field_yields=field_yields,
        prefix_grouped_yields=prefix_grouped_yields,
        yield_by_estate=yield_by_estate,
    )


@app.route('/logout')
def logout():
    username = session.get('username', '')
    session.clear()
    log_activity(username, "logged out")
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)

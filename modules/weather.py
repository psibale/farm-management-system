from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from datetime import datetime

weather_bp = Blueprint('weather', __name__)
WEATHER_FILE = "data/weather_data.xlsx"

@weather_bp.route('/weather-entry', methods=['GET', 'POST'])
def weather_entry():
    if request.method == 'POST':
        date = request.form.get('date')
        rainfall = request.form.get('rainfall')
        evapo = request.form.get('evapotranspiration')
        temp = request.form.get('temperature')

        if not date or not rainfall or not evapo or not temp:
            flash("All fields are required.", "danger")
            return redirect(url_for('weather.weather_entry'))

        try:
            rainfall = float(rainfall)
            evapo = float(evapo)
            temp = float(temp)
        except ValueError:
            flash("Rainfall, Evapotranspiration, and Temperature must be numeric.", "danger")
            return redirect(url_for('weather.weather_entry'))

        new_entry = {
            "Date": date,
            "Rainfall": rainfall,
            "Evapotranspiration": evapo,
            "Temperature": temp,
        }

        if not os.path.exists(WEATHER_FILE):
            df = pd.DataFrame(columns=["Date", "Rainfall", "Evapotranspiration", "Temperature"])
        else:
            df = pd.read_excel(WEATHER_FILE)

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(WEATHER_FILE, index=False)

        # 🔁 Trigger stress level recalculation
        try:
            from modules.recalc import recalculate_stress
            recalculate_stress()
            flash("✅ Weather data saved and stress levels updated.", "success")
        except Exception as e:
            flash(f"⚠️ Weather saved, but failed to recalculate stress levels: {e}", "warning")

        return redirect(url_for('weather.weather_entry'))

    return render_template('weather_entry.html')


import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for rendering charts
import matplotlib.pyplot as plt
import io
import base64

@weather_bp.route('/weather-report')
def weather_report():
    if not os.path.exists(WEATHER_FILE):
        flash("Weather data not found!", "danger")
        return redirect(url_for('weather.weather_entry'))

    df = pd.read_excel(WEATHER_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df.dropna(subset=["Date"], inplace=True)

    # Optional: Filter by active season if you’re storing it
    from modules.season import get_active_season
    current_season = get_active_season()
    if "Season" in df.columns:
        df = df[df["Season"] == current_season]

    if df.empty:
        flash("No weather data available for this season.", "info")
        return redirect(url_for('weather.weather_entry'))

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month

    grouped = df.groupby(["Year", "Month"]).agg({
        "Rainfall": "sum",
        "Evapotranspiration": "mean",
        "Temperature": "mean"
    }).reset_index()

    # Summary stats
    total_rainfall = df["Rainfall"].sum()
    avg_temp = df["Temperature"].mean()
    avg_evapo = df["Evapotranspiration"].mean()

    # Create chart image
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()

    x_labels = grouped["Year"].astype(str) + "-" + grouped["Month"].astype(str).str.zfill(2)

    ax1.bar(x_labels, grouped["Rainfall"], color='skyblue', label="Rainfall")
    ax2.plot(x_labels, grouped["Evapotranspiration"], color='green', marker='o', label="Evapotranspiration")

    ax1.set_ylabel("Rainfall (mm)", color='blue')
    ax2.set_ylabel("Evapotranspiration (mm)", color='green')
    ax1.set_xlabel("Month")
    ax1.tick_params(axis='x', rotation=45)
    ax1.set_title("Monthly Rainfall vs. Evapotranspiration")

    fig.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()

    return render_template("weather_report.html",
                           chart_url=chart_url,
                           grouped=grouped.to_dict(orient="records"),
                           total_rainfall=round(total_rainfall, 2),
                           avg_temp=round(avg_temp, 2),
                           avg_evapo=round(avg_evapo, 2),
                           season=current_season)

# modules/weather.py
import os
import pandas as pd
from flask import Blueprint, request, redirect, url_for, flash, render_template
from modules.season import get_active_season

weather_bp = Blueprint("weather", __name__)

WEATHER_FILE = "data/weather_data.xlsx"

@weather_bp.route("/weather-entry", methods=["GET", "POST"])
def weather_entry():
    if request.method == "POST":
        date = request.form.get("date")
        rainfall = request.form.get("rainfall")
        evapo = request.form.get("evapo")
        temp = request.form.get("temp")
        season = request.form.get("season")

        if not date or not season:
            flash("Date and Season are required", "danger")
            return redirect(request.url)

        new_entry = {
            "Date": date,
            "Rainfall": float(rainfall or 0),
            "Evapotranspiration": float(evapo or 0),
            "Temperature": float(temp or 0),
            "Season": season
        }

        if os.path.exists(WEATHER_FILE):
            df = pd.read_excel(WEATHER_FILE)
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        else:
            df = pd.DataFrame([new_entry])

        df.to_excel(WEATHER_FILE, index=False)

        flash("Weather record saved successfully", "success")
        return redirect(url_for("weather.weather_entry"))

    # ✅ LOAD DATA
    try:
        df = pd.read_excel(WEATHER_FILE)

        # ✅ FIX DATE SORTING
        active_season = get_active_season()

        df = df[df["Season"] == active_season]

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values(by="Date", ascending=False)

        weather_data = df.head(1).to_dict(orient="records")

    except Exception as e:
        print("ERROR LOADING WEATHER DATA:", e)
        weather_data = []

    return render_template("weather_entry.html", weather_data=weather_data)


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

@weather_bp.route('/weather-report/daily')
def weather_daily_report():
    if not os.path.exists(WEATHER_FILE):
        flash("No weather data found!", "danger")
        return redirect(url_for('weather.weather_entry'))

    df = pd.read_excel(WEATHER_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df.dropna(subset=["Date"], inplace=True)
    season = get_active_season()

    if "Season" in df.columns:
        df = df[df["Season"] == season]

    if df.empty:
        flash("No weather data available for this season.", "info")
        return redirect(url_for('weather.weather_entry'))

    df = df.sort_values("Date")

    return render_template(
        "weather_report_daily.html",
        daily=df.to_dict(orient="records"),
        season=season
    )

from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from modules.utils import role_required


from flask import request, render_template, redirect, url_for, flash, session
import pandas as pd
import os
from gdrive_sync import upload_excel_to_drive  # Only if you're using GDrive sync

IRRIGATION_FILE = "data/irrigation_records.xlsx"
WEATHER_FILE = "data/weather_data.xlsx"
WHC = 100
SM_i = 5

@agriculture_bp.route("/irrigation", methods=["GET", "POST"])
def irrigation():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        try:
            date = request.form["date"]
            field = request.form["field"]
            irrigation = float(request.form["irrigation"])

            new_entry = {
                "Date": pd.to_datetime(date).date(),
                "Field": field,
                "Irrigation Applied": irrigation
            }

            if os.path.exists(IRRIGATION_FILE):
                df = pd.read_excel(IRRIGATION_FILE)
            else:
                df = pd.DataFrame(columns=["Date", "Field", "Irrigation Applied"])

            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_excel(IRRIGATION_FILE, index=False)

            # Optional: Upload to Google Drive
            try:
                upload_excel_to_drive(IRRIGATION_FILE)
            except Exception as sync_err:
                print("Google Drive sync failed:", sync_err)

            flash("✅ Irrigation record saved successfully!", "success")
        except Exception as e:
            flash(f"❌ Failed to save record: {e}", "danger")

        return redirect(url_for("agriculture.irrigation"))

    return render_template("agriculture/irrigation.html")


@agriculture_bp.route("/moisture-graph", methods=["POST"])
def generate_moisture_graph():
    field = request.form["field"]
    start_date = pd.to_datetime(request.form["start_date"])
    end_date = pd.to_datetime(request.form["end_date"])

    weather = pd.read_excel(WEATHER_FILE)
    irrigation = pd.read_excel(IRRIGATION_FILE)
    weather["Date"] = pd.to_datetime(weather["Date"])
    irrigation["Date"] = pd.to_datetime(irrigation["Date"])
    irrigation = irrigation[irrigation["Field"] == field]

    dates = pd.date_range(start=weather["Date"].min(), end=weather["Date"].max())
    merged = pd.DataFrame({"Date": dates})
    merged = merged.merge(weather, on="Date", how="left").fillna(0)
    merged = merged.merge(irrigation[["Date", "Irrigation Applied"]], on="Date", how="left").fillna(0)

    moisture = [SM_i]
    for i in range(1, len(merged)):
        net_input = merged.loc[i, "Rainfall"] + merged.loc[i, "Irrigation Applied"] - merged.loc[i, "Evapotranspiration"]
        new_val = max(0, min(WHC, moisture[-1] + net_input))
        moisture.append(new_val)

    merged["Soil Moisture"] = moisture
    merged["Deficit"] = WHC - merged["Soil Moisture"]
    merged = merged[(merged["Date"] >= start_date) & (merged["Date"] <= end_date)]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(merged["Date"], merged["Deficit"], label="Deficit", color="black")
    ax.axhline(y=50, color='red', linestyle='--', label="Threshold")
    ax.set_title("Soil Moisture Deficit")
    ax.set_ylabel("Deficit (mm)")
    ax.set_xlabel("Date")
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.tick_params(axis='x', rotation=45)
    ax.legend()

    ax2 = ax.twinx()
    ax2.bar(merged["Date"], merged["Rainfall"], color='green', alpha=0.5, label="Rainfall")
    ax2.bar(merged["Date"], merged["Irrigation Applied"], color='blue', alpha=0.5, label="Irrigation", hatch='//')
    ax2.set_ylim(0, 120)

    img = io.BytesIO()
    plt.tight_layout()
    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template("agriculture/irrigation.html", graph=plot_url)

from flask import request, render_template, flash
import pandas as pd
import os
from utils.helpers import get_active_season, get_available_seasons  # Make sure these are available

IRRIGATION_FILE = "data/irrigation_records.xlsx"

@activity_bp.route("/agriculture/irrigation-report")
def irrigation_report():
    try:
        current_season = get_active_season()
        all_seasons = get_available_seasons()
        selected_season = request.args.get("season", default="")
        selected_field = request.args.get("field", default="")

        if not os.path.exists(IRRIGATION_FILE):
            flash("No irrigation records found.", "warning")
            return render_template("agriculture/irrigation_report.html",
                                   records=[],
                                   season=current_season,
                                   all_seasons=all_seasons,
                                   all_fields=[],
                                   selected_field=selected_field)

        df = pd.read_excel(IRRIGATION_FILE)

        # Extract unique field names for the filter dropdown
        all_fields = sorted(df["Field"].dropna().unique())

        # Apply filters if provided
        if selected_season:
            df = df[df["Season"] == selected_season]
        if selected_field:
            df = df[df["Field"] == selected_field]

        # Fallback season label if no filter is set
        display_season = selected_season if selected_season else current_season

        return render_template("agriculture/irrigation_report.html",
                               records=df.to_dict(orient="records"),
                               season=display_season,
                               all_seasons=all_seasons,
                               all_fields=all_fields,
                               selected_field=selected_field)

    except Exception as e:
        flash(f"Error loading irrigation report: {e}", "danger")
        return render_template("agriculture/irrigation_report.html",
                               records=[],
                               season="N/A",
                               all_seasons=[],
                               all_fields=[],
                               selected_field="")

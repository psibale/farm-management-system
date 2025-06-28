from flask import Blueprint, redirect, url_for
import pandas as pd
import os

recalc_bp = Blueprint("recalc", __name__)

GIS_FILE = "data/field_polygons.xlsx"
WEATHER_FILE = "data/weather_data.xlsx"
IRRIGATION_FILE = "data/irrigation_records.xlsx"

@recalc_bp.route("/recalculate_stress")
def recalculate_stress():
    try:
        if not os.path.exists(GIS_FILE) or not os.path.exists(WEATHER_FILE):
            return "Missing GIS or weather data."

        weather = pd.read_excel(WEATHER_FILE)
        irrigation = pd.read_excel(IRRIGATION_FILE) if os.path.exists(IRRIGATION_FILE) else pd.DataFrame(columns=["Date", "Field", "Irrigation Applied"])

        weather["Date"] = pd.to_datetime(weather["Date"])
        irrigation["Date"] = pd.to_datetime(irrigation["Date"])

        if "Rainfall" not in weather or "Evapotranspiration" not in weather:
            return "Weather data missing required columns."

        # Aggregate irrigation per field and date
        irrigation_sum = irrigation.groupby(["Date", "Field"])["Irrigation Applied"].sum().reset_index()

        df = pd.read_excel(GIS_FILE)

        stress_levels = []
        for _, row in df.iterrows():
            field = row["Field Name"]

            field_weather = weather.copy()
            field_irrig = irrigation_sum[irrigation_sum["Field"] == field]

            merged = pd.merge(field_weather, field_irrig, on="Date", how="left").fillna(0).infer_objects(copy=False)
            merged["Net Water"] = merged["Rainfall"] + merged["Irrigation Applied"] - merged["Evapotranspiration"]

            total_stress = merged["Net Water"].sum()

            if total_stress >= 50:
                level = "Low"
            elif 30 <= total_stress < 50:
                level = "Moderate"
            elif 10 <= total_stress < 30:
                level = "High"
            else:
                level = "Critical"

            stress_levels.append(level)

        df["Stress Level"] = stress_levels
        df.to_excel(GIS_FILE, index=False)

        return redirect(url_for("gis.view_fields"))

    except Exception as e:
        return f"Error: {e}"

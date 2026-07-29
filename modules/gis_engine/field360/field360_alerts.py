from datetime import datetime
import pandas as pd


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def days_since(date_string):
    """
    Returns number of days since a date.
    """

    if not date_string:
        return None

    try:

        date = pd.to_datetime(date_string)

        return (datetime.today() - date).days

    except Exception:

        return None


# ---------------------------------------------------
# FIELD ALERT ENGINE
# ---------------------------------------------------

def get_field_alerts(field360):

    alerts = []

    harvest = field360.get("harvest", {})
    irrigation = field360.get("irrigation", {})
    fertilizer = field360.get("fertilizer", {})
    weather = field360.get("weather", {})
    pest = field360.get("pest", {})

    # ===================================================
    # HARVEST
    # ===================================================

    if harvest.get("status") == "Harvested":

        alerts.append({

            "level": "success",

            "icon": "✅",

            "message": "Harvest completed."

        })

    # ===================================================
    # IRRIGATION
    # ===================================================

    irrigation_days = days_since(
        irrigation.get("last_irrigation")
    )

    if irrigation_days is not None:

        if irrigation_days > 7:

            alerts.append({

                "level": "danger",

                "icon": "💧",

                "message":
                    f"Irrigation overdue ({irrigation_days} days)."

            })

    # ===================================================
    # FERTILIZER
    # ===================================================

    crop_age = field360.get("crop_age", 0)

    if crop_age >= 2 and fertilizer.get("applications", 0) == 0:
        alerts.append({

            "level": "warning",

            "icon": "🌱",

            "message": "No fertilizer applied this season."

        })

    # ===================================================
    # WEATHER
    # ===================================================

    rainfall = weather.get("rainfall", 0)

    et = weather.get("evapotranspiration", 0)

    if rainfall < et:

        alerts.append({

            "level": "warning",

            "icon": "☀️",

            "message": "Rainfall below crop water demand."

        })

    # ===================================================
    # PEST
    # ===================================================

    if pest.get("ysa", 0) >= 20:

        alerts.append({

            "level": "danger",

            "icon": "🐛",

            "message":
                f"High YSA infestation ({pest['ysa']:.1f}%)."

        })

    if pest.get("smut", 0) >= 5:

        alerts.append({

            "level": "danger",

            "icon": "🦠",

            "message":
                f"Smut infection ({pest['smut']:.1f}%)."

        })

    # ===================================================
    # NO ALERTS
    # ===================================================

    if len(alerts) == 0:

        alerts.append({

            "level": "success",

            "icon": "🌾",

            "message": "No issues detected."

        })

    return alerts
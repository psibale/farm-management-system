def build_ai_recommendation(field360):

    harvest = field360.get("harvest", {})
    irrigation = field360.get("irrigation", {})
    fertilizer = field360.get("fertilizer", {})
    weather = field360.get("weather", {})
    pest = field360.get("pest", {})
    quality = field360.get("quality", {})

    actions = []
    assessment = []

    priority = "LOW"

    # -----------------------------------------
    # Harvest
    # -----------------------------------------

    if harvest.get("status") == "Harvested":

        assessment.append(
            "Harvest operations have been completed successfully."
        )

    else:

        assessment.append(
            "Harvest operations are still in progress."
        )

    # -----------------------------------------
    # Irrigation
    # -----------------------------------------

    if irrigation.get("status") == "Irrigated":

        days = irrigation.get("days_since", 0)

        if days > 14:

            priority = "HIGH"

            assessment.append(
                f"The last irrigation was {days} days ago, which exceeds the recommended interval."
            )

            actions.append(
                "Schedule irrigation immediately."
            )

        else:

            assessment.append(
                "Irrigation records indicate the field is being watered within the expected interval."
            )

    else:

        priority = "HIGH"

        assessment.append(
            "No irrigation has been recorded during the current season."
        )

        actions.append(
            "Inspect irrigation equipment and schedule watering."
        )

    # -----------------------------------------
    # Fertilizer
    # -----------------------------------------

    if fertilizer.get("status") == "No Application":

        assessment.append(
            "No fertilizer applications have been recorded this season."
        )

        actions.append(
            "Review the fertilizer programme."
        )

        if priority != "HIGH":
            priority = "MEDIUM"

    else:

        assessment.append(
            "Fertilizer applications have been recorded for this field."
        )

    # -----------------------------------------
    # Weather
    # -----------------------------------------

    rainfall = weather.get("rainfall", 0)
    et = weather.get("evapotranspiration", 0)

    if rainfall < et:

        assessment.append(
            "Current evapotranspiration exceeds recent rainfall, indicating increasing crop water demand."
        )

        actions.append(
            "Monitor soil moisture closely."
        )

    else:

        assessment.append(
            "Recent rainfall is adequate for current crop water demand."
        )

    # -----------------------------------------
    # Pest
    # -----------------------------------------

    status = pest.get("status", "")

    if status == "Treatment Required":

        priority = "HIGH"

        assessment.append(
            "Pest pressure requires immediate intervention."
        )

        actions.append(
            "Apply the recommended pest control programme."
        )

    elif status == "Monitor":

        assessment.append(
            "Minor pest activity has been detected."
        )

        actions.append(
            "Continue weekly pest scouting."
        )

    elif status == "Healthy":

        assessment.append(
            "No significant pest or disease pressure has been detected."
        )

    # -----------------------------------------
    # GIS QUALITY
    # -----------------------------------------

    if quality.get("status") == "Excellent":

        assessment.append(
            "GIS boundary quality is excellent and suitable for operational planning."
        )

    else:

        assessment.append(
            "GIS quality should be reviewed before operational planning."
        )

        actions.append(
            "Inspect field boundaries."
        )

    # -----------------------------------------
    # Overall Risk
    # -----------------------------------------

    if priority == "HIGH":
        risk = "High"

    elif priority == "MEDIUM":
        risk = "Medium"

    else:
        risk = "Low"

    # -----------------------------------------
    # Final Recommendation
    # -----------------------------------------

    recommendation = " ".join(assessment)

    return {

        "priority": priority,

        "risk": risk,

        "recommendation": recommendation,

        "actions": actions

    }
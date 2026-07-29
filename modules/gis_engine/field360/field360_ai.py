def build_ai_recommendation(field360):

    harvest = field360.get("harvest", {})
    irrigation = field360.get("irrigation", {})
    fertilizer = field360.get("fertilizer", {})
    weather = field360.get("weather", {})
    pest = field360.get("pest", {})
    quality = field360.get("quality", {})

    actions = []

    priority = "LOW"

    # -----------------------------------------
    # Harvest
    # -----------------------------------------

    if harvest.get("status") == "Harvested":

        actions.append(
            "Harvest completed successfully."
        )

    # -----------------------------------------
    # Irrigation
    # -----------------------------------------

    if irrigation.get("status") == "Irrigated":

        days = irrigation.get("days_since", 0)

        if days > 14:

            priority = "HIGH"

            actions.append(
                f"Apply irrigation immediately ({days} days since last irrigation)."
            )

    else:

        priority = "HIGH"

        actions.append(
            "No irrigation recorded this season."
        )

    # -----------------------------------------
    # Fertilizer
    # -----------------------------------------

    if fertilizer.get("status") == "No Application":

        priority = "MEDIUM"

        actions.append(
            "Review fertilizer programme."
        )

    # -----------------------------------------
    # Weather
    # -----------------------------------------

    rain = weather.get("rainfall", 0)

    et = weather.get("evapotranspiration", 0)

    if rain < et:

        actions.append(
            "Crop water demand exceeds rainfall."
        )

    # -----------------------------------------
    # Pest
    # -----------------------------------------

    if pest.get("status") == "Treatment Required":

        priority = "HIGH"

        actions.append(
            "Schedule pest treatment."
        )

    elif pest.get("status") == "Monitor":

        actions.append(
            "Continue weekly pest scouting."
        )

    # -----------------------------------------
    # GIS
    # -----------------------------------------

    if quality.get("status") != "Excellent":

        actions.append(
            "Review GIS boundary quality."
        )

    # -----------------------------------------
    # Recommendation
    # -----------------------------------------

    recommendation = " ".join(actions)

    return {

        "priority": priority,

        "risk": priority.title(),

        "recommendation": recommendation,

        "actions": actions

    }
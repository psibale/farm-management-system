# routes/programme.py
from flask import Blueprint, render_template
from modules.ai_farm_manager import ai_farm_manager_programme
from collections import defaultdict

programme = Blueprint('programme', __name__)

@programme.route("/programme_schedule")
def programme_schedule():
    # Get current season
    current_season = get_active_season()

    # Generate programme (already returning list of dicts)
    programme = get_programme_for_stage(current_season)

    # ✅ Group by Stage before rendering
    programme_by_stage = {}
    for entry in programme:
        stage = entry["Stage"]   # e.g. 🌿 Tillering
        if stage not in programme_by_stage:
            programme_by_stage[stage] = []
        programme_by_stage[stage].append(entry)

    return render_template(
        "programme_schedule.html",
        programme_by_stage=programme_by_stage,
        current_season=current_season
    )

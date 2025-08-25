# routes/programme.py
from flask import Blueprint, render_template
from modules.ai_farm_manager import ai_farm_manager_programme
from collections import defaultdict

programme = Blueprint('programme', __name__)

@programme.route('/programme_schedule')
def programme_schedule():
    # Get AI-generated programme
    weekly_programme = ai_farm_manager_programme()

    # Group fields by crop stage
    grouped_programme = defaultdict(list)
    for entry in weekly_programme:
        grouped_programme[entry["Stage"]].append(entry)

    # Sort stages in logical crop order
    stage_order = ["🌱 Establishment", "🌿 Tillering", "🌾 Grand Growth", "🍂 Maturity", "🚜 Harvest Ready"]
    grouped_programme_sorted = {
        stage: grouped_programme.get(stage, [])
        for stage in stage_order
    }

    # Optional placeholder season (remove if you don’t want to display)
    current_season = "2025 Main Season"

    return render_template(
        'programme_schedule.html',
        grouped_programme=grouped_programme_sorted,
        current_season=current_season
    )

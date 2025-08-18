# routes/programme.py
from flask import Blueprint, render_template
from modules.ai_farm_manager import ai_farm_manager_programme
from collections import defaultdict

programme = Blueprint('programme', __name__)

@programme.route('/programme_schedule')
def programme_schedule():
    # Get the AI-generated weekly programme
    weekly_programme = ai_farm_manager_programme()

    # Group fields by crop stage
    grouped_programme = defaultdict(list)
    for entry in weekly_programme:
        grouped_programme[entry["Stage"]].append(entry)

    # Sort stages by logical order (optional)
    stage_order = ["🌱 Germination", "🌿 Tillering", "🌾 Grand Growth", "🍂 Maturity", "🚜 Harvest Ready"]
    grouped_programme_sorted = {stage: grouped_programme.get(stage, []) for stage in stage_order}

    # Pass grouped_programme to the template
    return render_template(
        'programme_schedule.html',
        grouped_programme=grouped_programme_sorted
    )

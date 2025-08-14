from flask import Blueprint, render_template
from modules.season import get_active_season
from modules.ai_farm_manager import ai_farm_manager_programme

programme = Blueprint('programme', __name__)

@programme.route('/programme_schedule')
def programme_schedule():
    current_season = get_active_season()
    programme_data = ai_farm_manager_programme()  # use the imported function

    return render_template(
        'programme_schedule.html',
        programme=programme_data,
        current_season=current_season
    )

from flask import Blueprint, render_template
from reports.yield_season_comparison import get_yield_season_summary
from farm_utils.pest_disease_utils import get_pest_disease_season_summary
from farm_utils.field_leaderboard import get_field_leaderboard
from farm_utils.irrigation_efficiency import get_yield_vs_irrigation_efficiency
from farm_utils.yield_trends import get_yield_trends_by_season

management_bp = Blueprint('management', __name__)

@management_bp.route('/management/dashboard')
def management_dashboard():

    yield_df = get_yield_season_summary()
    pest_df = get_pest_disease_season_summary()

    # Latest season
    latest_yield = yield_df.iloc[-1].to_dict() if not yield_df.empty else {}
    latest_pest = pest_df.iloc[-1].to_dict() if not pest_df.empty else {}

    # Chart data
    seasons = yield_df["Season"].tolist()
    total_tons = yield_df["Total_Tons"].tolist()
    avg_tch = yield_df["Season_TCH"].tolist()

    best_fields, worst_fields, _ = get_field_leaderboard()
    efficiency_data = get_yield_vs_irrigation_efficiency()

    tons_trend, tch_trend = get_yield_trends_by_season()

    return render_template(
        'management/dashboard.html',
        latest_yield=latest_yield,
        latest_pest=latest_pest,
        seasons=seasons,
        total_tons=total_tons,
        avg_tch=avg_tch,
        best_fields=best_fields,
        worst_fields=worst_fields,
        efficiency_data=efficiency_data,
        tons_trend=tons_trend,
        tch_trend=tch_trend
    )








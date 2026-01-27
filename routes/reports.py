from flask import Blueprint, render_template
from reports.yield_season_comparison import get_yield_season_summary
from farm_utils.pest_disease_utils import get_pest_disease_season_summary
from farm_utils.pest_disease_trends import get_smut_ysa_trend
from farm_utils.chronic_fields import get_chronic_fields
from farm_utils.chemical_effectiveness import get_chemical_effectiveness


reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/yield-season-comparison')
def yield_season_comparison():
    summary = get_yield_season_summary()
    return render_template(
        'reports/yield_season_comparison.html',
        tables=summary.to_dict(orient='records')
    )

@reports_bp.route('/reports/pest-disease-season')
def pest_disease_season_comparison():
    df = get_pest_disease_season_summary()
    tables = df.to_dict(orient='records')
    latest = tables[-1] if tables else None

    # NEW: Trend data
    trend_df = get_smut_ysa_trend()
    trend_data = trend_df.to_dict(orient='records')

    chronic_df = get_chronic_fields(top_n=5)
    chronic_fields = chronic_df.to_dict(orient='records')

    chem_df = get_chemical_effectiveness()
    chemicals = chem_df.to_dict(orient='records')

    # Chart data
    seasons = df["Season"].tolist()
    events = df["Events"].tolist()
    avg_smut = df["Avg_SMUT"].round(2).tolist()
    avg_ysa = df["Avg_YSA"].round(2).tolist()

    return render_template(
        'reports/pest_disease_season_comparison.html',
        tables=tables,
        latest=latest,
        seasons=seasons,
        events=events,
        avg_smut=avg_smut,
        avg_ysa=avg_ysa,
        trend_data=trend_data,
        chronic_fields=chronic_fields,
        chemicals=chemicals # 👈
    )

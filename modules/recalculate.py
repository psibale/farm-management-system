from flask import Blueprint, redirect, url_for

recalc_bp = Blueprint("recalc", __name__)


@recalc_bp.route("/recalculate_stress")
def recalculate_stress():
    """Refresh mapped-field stress using the shared GIS calculation."""
    try:
        from modules.gis import recalculate_field_stress_levels

        recalculate_field_stress_levels()
        return redirect(url_for("gis.view_fields"))
    except Exception as e:
        return f"Error: {e}"

from flask import Blueprint, render_template

mill_reports_bp = Blueprint('mill_reports', __name__, url_prefix='/mill-reports')

@mill_reports_bp.route('/')
def mill_reports_dashboard():
    return render_template('mill_reports_dashboard.html', title='Mill Reports')

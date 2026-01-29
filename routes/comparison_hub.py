from flask import Blueprint, render_template

comparison_bp = Blueprint('comparison', __name__)

@comparison_bp.route('/comparisons')
def comparisons_home():
    return render_template('comparisons/home.html')

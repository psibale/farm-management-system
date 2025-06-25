# modules/farm_activities.py

from flask import Blueprint, render_template, session, redirect, url_for

farm_activities_bp = Blueprint('farm_activities', __name__)

@farm_activities_bp.route("/agriculture/farm-activities")
def farm_activities():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("agriculture/farm_activities.html", username=session['username'])

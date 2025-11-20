# routes/harvest_routes.py
from flask import Blueprint, render_template, request, send_file, current_app, url_for
import io
import csv
import pandas as pd
from datetime import datetime
from modules.harvest_planner import load_all, generate_field_estimates, build_weekly_schedule, DEFAULT_MILL_WEEKLY_CAPACITY

harvest_bp = Blueprint("harvest", __name__, url_prefix="/harvest")

@harvest_bp.route("/auto-harvest-program")
def auto_harvest_program():
    # optional query params
    capacity = request.args.get("capacity", type=float) or DEFAULT_MILL_WEEKLY_CAPACITY
    # load data
    data = load_all()
    estimates = generate_field_estimates(data)
    # optionally choose start_from param (YYYY-MM-DD)
    start_from = request.args.get("start_from")
    if start_from:
        try:
            start_from = pd.to_datetime(start_from).date()
        except Exception:
            start_from = None
    schedule = build_weekly_schedule(estimates, weekly_capacity=capacity, start_from=start_from)
    # render template
    return render_template("auto_harvest_program.html",
                            estimates=estimates,
                            schedule=schedule,
                            capacity=capacity)

@harvest_bp.route("/auto-harvest-program/download")
def download_auto_harvest_program():
    # generate CSV containing field estimates + schedule as two sheets (CSV will contain estimates)
    data = load_all()
    estimates = generate_field_estimates(data)
    # build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field","Area_ha","Stress","Est_TCH","Est_Tons","Est_Harvest_Date"])
    for e in estimates:
        writer.writerow([e["Field"], e["Area_ha"], e["Stress"], e["Est_TCH"], e["Est_Tons"], e["Est_Harvest_Date"]])
    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"auto_harvest_program_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype="text/csv")

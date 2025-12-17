# routes/monthly_safety_report.py
import os
import io
import uuid
import json
import ast
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort, send_file
)

import os
import platform
import shutil

# PDFKit / wkhtmltopdf configuration
pdf_config = None

if platform.system() == "Windows":
    WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if os.path.exists(WKHTMLTOPDF_PATH):
        import pdfkit
        pdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
else:
    WKHTMLTOPDF_PATH = shutil.which("wkhtmltopdf")
    if WKHTMLTOPDF_PATH:
        import pdfkit
        pdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# --------------------------------------------------
# Blueprint
# --------------------------------------------------
monthly_safety_bp = Blueprint(
    "monthly_safety",
    __name__,
    template_folder="../templates/safety",
    url_prefix="/safety/monthly-reports"
)

# --------------------------------------------------
# Paths
# --------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
EXCEL_FILE = os.path.join(DATA_DIR, "monthly_safety_reports.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)

# --------------------------------------------------
# Excel structure
# --------------------------------------------------
REQUIRED_COLUMNS = [
    "ID",
    "Report_Number",
    "Report_Month",
    "Prepared_By",
    "Position",

    # Tables / JSON blocks
    "SHE_Staff_Table",       # JSON
    "Accident_Stats",        # JSON
    "Challenges",            # JSON

    # Narrative sections
    "Induction_Text",
    "Accidents_Summary",
    "Risk_Assessment",
    "Tractors_Equipment",
    "Obituary",

    # System
    "Version",
    "Created_At",
    "Updated_At"
]

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def ensure_file():
    """Create Excel file if missing."""
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_excel(EXCEL_FILE, index=False)


def ensure_columns():
    """Auto-add missing columns safely."""
    df = pd.read_excel(EXCEL_FILE).fillna("")
    updated = False

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            updated = True

    if updated:
        write_excel_atomic(df)


def read_excel():
    ensure_file()
    ensure_columns()
    return pd.read_excel(EXCEL_FILE, dtype=str).fillna("")


def write_excel_atomic(df):
    base, ext = os.path.splitext(EXCEL_FILE)
    tmp = f"{base}_tmp{ext}"
    df.to_excel(tmp, index=False)
    os.replace(tmp, EXCEL_FILE)


def make_id():
    return uuid.uuid4().hex


def make_report_number():
    """MSR-YYYY-MM-XXX"""
    now = datetime.utcnow()
    stamp = now.strftime("%Y-%m")
    df = read_excel()
    same_month = df[df["Report_Month"] == stamp]
    seq = len(same_month) + 1
    return f"MSR-{stamp}-{seq:03d}"


def safe_json_load(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        try:
            return ast.literal_eval(value)
        except Exception:
            return []

# --------------------------------------------------
# List Reports
# --------------------------------------------------
@monthly_safety_bp.route("/")
def report_list():
    df = read_excel()
    records = df.sort_values("Created_At", ascending=False).to_dict("records")
    return render_template(
        "monthly_safety_report_list.html",
        records=records
    )


# --------------------------------------------------
# New Report
# --------------------------------------------------
@monthly_safety_bp.route("/new", methods=["GET", "POST"])
def new_report():
    if request.method == "POST":
        nid = make_id()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        rec = {
            "ID": nid,
            "Report_Number": make_report_number(),
            "Report_Month": request.form.get("report_month"),
            "Prepared_By": request.form.get("prepared_by"),
            "Position": request.form.get("position"),

            # JSON tables
            "SHE_Staff_Table": json.dumps([]),
            "Accident_Stats": json.dumps([]),
            "Challenges": json.dumps([]),

            # Narrative sections
            "Induction_Text": request.form.get("induction_text"),
            "Accidents_Summary": request.form.get("accidents_summary"),
            "Risk_Assessment": request.form.get("risk_assessment"),
            "Tractors_Equipment": request.form.get("tractors_equipment"),
            "Obituary": request.form.get("obituary"),

            "Version": 1,
            "Created_At": now,
            "Updated_At": now
        }

        df = read_excel()
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        write_excel_atomic(df)

        flash("Monthly Safety Report created successfully.", "success")
        return redirect(url_for("monthly_safety.view_report", id=nid))

    return render_template("monthly_safety_report_form.html")


# --------------------------------------------------
# View Report
# --------------------------------------------------
@monthly_safety_bp.route("/<id>")
def view_report(id):
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # Parse JSON fields
    rec["SHE_Staff_Table"] = safe_json_load(rec.get("SHE_Staff_Table"))
    rec["Accident_Stats"] = safe_json_load(rec.get("Accident_Stats"))
    rec["Challenges"] = safe_json_load(rec.get("Challenges"))

    return render_template(
        "monthly_safety_report_view.html",
        rec=rec
    )

# --------------------------------------------------
# Export PDF
# --------------------------------------------------
@monthly_safety_bp.route("/<id>/export")
def export_pdf(id):
    if not pdf_config:
        abort(500, "PDF export not configured (wkhtmltopdf missing)")

    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # Parse JSON fields
    rec["SHE_Staff_Table"] = safe_json_load(rec.get("SHE_Staff_Table"))
    rec["Accident_Stats"] = safe_json_load(rec.get("Accident_Stats"))
    rec["Challenges"] = safe_json_load(rec.get("Challenges"))

    # Absolute logo path (wkhtmltopdf safe)
    host = request.host_url.rstrip("/")
    rec["LOGO"] = f"{host}{url_for('static', filename='safety/company_logo.png')}"

    try:
        html = render_template(
            "monthly_safety_report_pdf.html",
            rec=rec,
            for_pdf=True
        )
        pdf_bytes = pdfkit.from_string(
            html,
            False,
            configuration=pdf_config
        )
    except Exception as e:
        current_app.logger.exception("Monthly Safety PDF failed")
        abort(500, f"PDF generation failed: {e}")

    filename = f"Monthly_Safety_Report_{rec['Report_Month']}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

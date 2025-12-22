import os
import io
import uuid
import json
import ast
import platform
import shutil
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort, send_file, current_app
)

# --------------------------------------------------
# wkhtmltopdf / PDFKit configuration
# --------------------------------------------------
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

    # JSON blocks
    "SHE_Staff_Table",
    "SHE_Staff_Comment",
    "Accident_Stats",
    "Challenges",

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
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_excel(EXCEL_FILE, index=False)


def ensure_columns():
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
    now = datetime.utcnow()
    stamp = now.strftime("%Y-%m")
    df = read_excel()
    same_month = df[df["Report_Month"] == stamp]
    seq = len(same_month) + 1
    return f"MSR-{stamp}-{seq:03d}"


def to_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def safe_json_load(value, default=None):
    if default is None:
        default = []

    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        try:
            return ast.literal_eval(value)
        except Exception:
            return default


def calculate_staff_totals(staff):
    return {
        "permanent": sum(to_int(v.get("permanent")) for v in staff.values()),
        "seasonal": sum(to_int(v.get("seasonal")) for v in staff.values()),
        "casual": sum(to_int(v.get("casual")) for v in staff.values()),
    }

def calculate_staff_totals(staff_table):
    total_p = total_s = total_c = 0

    if not isinstance(staff_table, dict):
        return {
            "permanent": 0,
            "seasonal": 0,
            "casual": 0
        }

    for _, vals in staff_table.items():
        total_p += to_int(vals.get("permanent"))
        total_s += to_int(vals.get("seasonal"))
        total_c += to_int(vals.get("casual"))

    return {
        "permanent": total_p,
        "seasonal": total_s,
        "casual": total_c
    }

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

        staff = {
            "Human Resources": {
                "permanent": to_int(request.form.get("staff_Human Resources_permanent")),
                "seasonal": to_int(request.form.get("staff_Human Resources_seasonal")),
                "casual": to_int(request.form.get("staff_Human Resources_casual")),
            },
            "General Agriculture": {
                "permanent": to_int(request.form.get("staff_General Agriculture_permanent")),
                "seasonal": to_int(request.form.get("staff_General Agriculture_seasonal")),
                "casual": to_int(request.form.get("staff_General Agriculture_casual")),
            },
            "Accounts Department": {
                "permanent": to_int(request.form.get("staff_Accounts Department_permanent")),
                "seasonal": to_int(request.form.get("staff_Accounts Department_seasonal")),
                "casual": to_int(request.form.get("staff_Accounts Department_casual")),
            }
        }

        rec = {
            "ID": nid,
            "Report_Number": make_report_number(),
            "Report_Month": request.form.get("report_month"),
            "Prepared_By": request.form.get("prepared_by"),
            "Position": request.form.get("position"),

            "SHE_Staff_Table": json.dumps(staff),
            "SHE_Staff_Comment": request.form.get("staff_comment", ""),
            "Accident_Stats": json.dumps([]),
            "Challenges": json.dumps([
                c.strip()
                for c in request.form.get("challenges_text", "").splitlines()
                if c.strip()
            ]),

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

    return render_template("monthly_safety_report_form.html", data={})

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

    # Parse JSON safely
    staff = safe_json_load(rec.get("SHE_Staff_Table", {}))
    rec["SHE_Staff_Table"] = staff
    rec["Challenges"] = safe_json_load(rec.get("Challenges", []))

    # -----------------------------
    # CALCULATE GRAND TOTALS (SERVER SIDE)
    # -----------------------------
    total_p = total_s = total_c = 0

    for _, vals in staff.items():
        total_p += to_int(vals.get("permanent"))
        total_s += to_int(vals.get("seasonal"))
        total_c += to_int(vals.get("casual"))

    rec["TOTAL_PERMANENT"] = total_p
    rec["TOTAL_SEASONAL"] = total_s
    rec["TOTAL_CASUAL"] = total_c

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
        abort(500, "wkhtmltopdf not configured")

    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # -----------------------------
    # Parse JSON SAFELY
    # -----------------------------
    rec["SHE_Staff_Table"] = safe_json_load(
        rec.get("SHE_Staff_Table")
    )

    rec["Accident_Stats"] = safe_json_load(
        rec.get("Accident_Stats")
    )

    rec["Challenges"] = safe_json_load(
        rec.get("Challenges")
    )

    # -----------------------------
    # CALCULATE GRAND TOTALS (PDF)
    # -----------------------------
    totals = calculate_staff_totals(rec["SHE_Staff_Table"])

    rec["TOTAL_PERMANENT"] = totals["permanent"]
    rec["TOTAL_SEASONAL"] = totals["seasonal"]
    rec["TOTAL_CASUAL"] = totals["casual"]

    # Absolute logo path (wkhtmltopdf-safe)
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

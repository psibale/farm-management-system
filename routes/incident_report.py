# routes/incident_report.py
import os
import uuid
import pdfkit
import io
from datetime import datetime
import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, abort
)
from werkzeug.utils import secure_filename
import platform
import shutil

# -----------------------
# PDFKit configuration
# -----------------------
if platform.system() == "Windows":
    WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if not os.path.exists(WKHTMLTOPDF_PATH):
        raise RuntimeError(f"wkhtmltopdf not found at {WKHTMLTOPDF_PATH}. Install it.")
else:
    WKHTMLTOPDF_PATH = shutil.which("wkhtmltopdf")
    if not WKHTMLTOPDF_PATH:
        raise RuntimeError("wkhtmltopdf executable not found. Install it in your Linux environment.")
pdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# -----------------------
# Blueprint
# -----------------------
incident_report_bp = Blueprint(
    "incident_report",
    __name__,
    template_folder="../templates/safety",
    url_prefix="/safety/incidents"
)

# -----------------------
# Paths & directories
# -----------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "static", "safety_reports")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXCEL_FILE = os.path.join(DATA_DIR, "incidents_full_report.xlsx")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}

# -----------------------
# Excel helpers
# -----------------------
def ensure_file():
    if not os.path.exists(EXCEL_FILE):
        cols = [
            "ID","Incident_Date","Incident_Time","Reported_By","Department","Location",
            "Incident_Type","Immediate_Action","Injury_Severity","Description",
            "Affected_Persons","Contributing_Factors","Root_Cause","Findings",
            "Risk_Level","Media_Interest","Reputational_Risk",
            "Corrective_Actions","Investigator","Investigation_Date",
            "Prepared_By","Prepared_Date","Photos","Created_At"
        ]
        pd.DataFrame(columns=cols).to_excel(EXCEL_FILE, index=False)

def read_excel():
    ensure_file()
    try:
        return pd.read_excel(EXCEL_FILE, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()

def write_excel(df):
    base, ext = os.path.splitext(EXCEL_FILE)
    tmp = f"{base}_tmp{ext}"
    os.makedirs(os.path.dirname(EXCEL_FILE), exist_ok=True)
    df.to_excel(tmp, index=False)
    os.replace(tmp, EXCEL_FILE)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT

# -----------------------
# Routes
# -----------------------

# New incident report
@incident_report_bp.route("/new-report", methods=["GET", "POST"])
def new_report():
    if request.method == "POST":
        form = request.form
        nid = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()

        rec = {
            "ID": nid,
            "Incident_Date": form.get("Incident_Date", ""),
            "Incident_Time": form.get("Incident_Time", ""),
            "Reported_By": form.get("Reported_By", ""),
            "Department": form.get("Department", ""),
            "Location": form.get("Location", ""),
            "Incident_Type": form.get("Incident_Type", ""),
            "Immediate_Action": form.get("Immediate_Action", ""),
            "Injury_Severity": form.get("Injury_Severity", ""),
            "Description": form.get("Description", ""),
            "Contributing_Factors": form.get("Contributing_Factors", ""),
            "Root_Cause": form.get("Root_Cause", ""),
            "Findings": form.get("Findings", ""),
            "Risk_Level": form.get("Risk_Level", ""),
            "Media_Interest": form.get("Media_Interest", ""),
            "Reputational_Risk": form.get("Reputational_Risk", ""),
            "Investigator": form.get("Investigator", ""),
            "Investigation_Date": form.get("Investigation_Date", ""),
            "Prepared_By": form.get("Prepared_By", ""),
            "Prepared_Date": form.get("Prepared_Date", ""),
            "Photos": "",
            "Created_At": now
        }

        # Affected persons
        affected = []
        for i in range(1, 6):
            name = form.get(f"person_name_{i}")
            if name and name.strip():
                affected.append({
                    "name": name.strip(),
                    "role": form.get(f"person_role_{i}", "").strip(),
                    "injury": form.get(f"person_injury_{i}", "").strip()
                })
        rec["Affected_Persons"] = str(affected)

        # Corrective actions
        actions = []
        idxs = form.getlist("action_item_index") or []
        for idx in idxs:
            try:
                i = str(idx)
                action_text = form.get(f"action_item_{i}", "").strip()
                if not action_text:
                    continue
                actions.append({
                    "action": action_text,
                    "responsible": form.get(f"action_resp_{i}", "").strip(),
                    "due": form.get(f"action_due_{i}", "").strip(),
                    "status": form.get(f"action_status_{i}", "Open").strip()
                })
            except Exception:
                continue
        rec["Corrective_Actions"] = str(actions)

        # Photos
        files = request.files.getlist("photos") or []
        saved = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                fn = secure_filename(f.filename)
                unique = f"{nid}_{uuid.uuid4().hex}_{fn}"
                path = os.path.join(UPLOAD_DIR, unique)
                f.save(path)
                saved.append(unique)
        if saved:
            rec["Photos"] = ";".join(saved)

        # Save to Excel
        df = read_excel()
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        write_excel(df)

        flash("Incident saved.", "success")
        return redirect(url_for("incident_report.view_report", id=nid))

    return render_template("incident_report_form.html", data={})

# View report
@incident_report_bp.route("/<id>")
def view_report(id):
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    import ast
    try:
        rec["Affected_Persons"] = ast.literal_eval(rec.get("Affected_Persons", "[]"))
    except:
        rec["Affected_Persons"] = []

    try:
        rec["Corrective_Actions"] = ast.literal_eval(rec.get("Corrective_Actions", "[]"))
    except:
        rec["Corrective_Actions"] = []

    return render_template("incident_report_pdf.html", rec=rec, for_pdf=False)

# Export PDF
@incident_report_bp.route("/report/<id>/pdf")
def export_pdf(id):
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)
    rec = row.iloc[0].to_dict()

    import ast
    try:
        rec["Affected_Persons"] = ast.literal_eval(rec.get("Affected_Persons", "[]"))
    except:
        rec["Affected_Persons"] = []

    try:
        rec["Corrective_Actions"] = ast.literal_eval(rec.get("Corrective_Actions", "[]"))
    except:
        rec["Corrective_Actions"] = []

    html = render_template("incident_report_pdf.html", rec=rec, for_pdf=True)
    pdf_bytes = pdfkit.from_string(html, False, configuration=pdf_config)

    filename = f"incident_report_{id}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# List all reports
@incident_report_bp.route("/")
def report_list():
    df = read_excel()
    return render_template(
        "incident_report_list.html",
        records=df.to_dict(orient="records")
    )

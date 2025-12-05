# routes/incident_report.py
import os
import uuid
import io
import ast
import json
import platform
import shutil
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, abort, current_app
)
from werkzeug.utils import secure_filename

# Optional QR generation lib; fallback to Google Chart QR URL if not available
try:
    import qrcode
    QR_LIB = "qrcode"
except Exception:
    qrcode = None
    QR_LIB = "google"

# PDFKit / wkhtmltopdf configuration
if platform.system() == "Windows":
    WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if not os.path.exists(WKHTMLTOPDF_PATH):
        # do not raise here — allow server to continue but PDF export will fail with clear error
        WKHTMLTOPDF_PATH = None
else:
    WKHTMLTOPDF_PATH = shutil.which("wkhtmltopdf")

pdf_config = None
if WKHTMLTOPDF_PATH:
    try:
        import pdfkit
        pdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    except Exception:
        pdf_config = None

# Blueprint + template folder & prefix
incident_report_bp = Blueprint(
    "incident_report",
    __name__,
    template_folder="../templates/safety",
    url_prefix="/safety/incidents"
)

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "static", "safety_reports")
QR_DIR = os.path.join(UPLOAD_DIR, "qrcodes")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

EXCEL_FILE = os.path.join(DATA_DIR, "incidents_full_report.xlsx")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "svg"}


# ----------------------------
# Helpers
# ----------------------------
def ensure_file():
    """Create Excel file if not present."""
    if not os.path.exists(EXCEL_FILE):
        cols = [
            "ID", "Report_Number", "Version", "Incident_Date", "Incident_Time",
            "Reported_By", "Department", "Location", "Incident_Type",
            "Immediate_Action", "Injury_Severity", "Description",
            "Affected_Persons", "Affected_Persons_Details",
            "Sequence_of_Events", "Contributing_Factors", "Root_Cause",
            "Findings", "Risk_Level", "Media_Interest", "Reputational_Risk",
            "Corrective_Actions",
            "Supervisor_Name", "Supervisor_Date",
            "HSO_Name", "HSO_Date",
            "Manager_Name", "Manager_Date",
            "Approvals",
            "Photos", "QR_Path",
            "Created_At", "Updated_At"
        ]
        pd.DataFrame(columns=cols).to_excel(EXCEL_FILE, index=False)

def ensure_columns():
    """Ensure all required columns exist in the Excel file."""
    required_cols = [
        "ID", "Report_Number", "Version", "Incident_Date", "Incident_Time",
        "Reported_By", "Department", "Location", "Incident_Type",
        "Immediate_Action", "Injury_Severity", "Description",
        "Affected_Persons", "Affected_Persons_Details",
        "Sequence_of_Events", "Contributing_Factors", "Root_Cause",
        "Findings", "Risk_Level", "Media_Interest", "Reputational_Risk",
        "Corrective_Actions",
        "Supervisor_Name", "Supervisor_Date",
        "HSO_Name", "HSO_Date",
        "Manager_Name", "Manager_Date",
        "Approvals",
        "Photos", "QR_Path",
        "Created_At", "Updated_At"
    ]

    df = pd.read_excel(EXCEL_FILE).fillna("")
    updated = False

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""      # Add missing column
            updated = True

    if updated:
        write_excel_atomic(df)


def read_excel():
    ensure_file()
    ensure_columns()       # <<< NEW LINE
    return pd.read_excel(EXCEL_FILE, dtype=str).fillna("")


def write_excel_atomic(df):
    """Write df to a temp file then replace original atomically."""
    base, ext = os.path.splitext(EXCEL_FILE)
    tmp = f"{base}_tmp{ext}"
    # ensure directory exists
    os.makedirs(os.path.dirname(EXCEL_FILE), exist_ok=True)
    df.to_excel(tmp, index=False)
    os.replace(tmp, EXCEL_FILE)


def make_id():
    return uuid.uuid4().hex


def make_report_number():
    """Return a readable report number like RPT-YYYYMMDD-XXXX"""
    now = datetime.utcnow()
    stamp = now.strftime("%Y%m%d")
    # count existing today reports to increment suffix
    df = read_excel()
    today = df[df.get("Created_At", "").str.startswith(stamp)]
    suffix = len(today) + 1
    return f"RPT-{stamp}-{suffix:04d}"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def save_uploaded_photos(files, prefix):
    saved = []
    for f in files or []:
        if f and getattr(f, "filename", None) and allowed_file(f.filename):
            fn = secure_filename(f.filename)
            unique = f"{prefix}_{uuid.uuid4().hex}_{fn}"
            dest = os.path.join(UPLOAD_DIR, unique)
            f.save(dest)
            saved.append(unique)
    return saved


def generate_qr_image(value, filename=None):
    """
    Generate a QR PNG saved in QR_DIR. If qrcode lib absent, return Google Chart URL.
    Returns a tuple (is_local, path_or_url).
      - is_local True: path relative to /static/...
      - is_local False: URL string
    """
    if QR_LIB == "qrcode" and qrcode is not None:
        try:
            img = qrcode.make(value)
            if not filename:
                filename = f"qr_{uuid.uuid4().hex}.png"
            dest = os.path.join(QR_DIR, filename)
            img.save(dest)
            # Return a path relative to static folder
            rel = os.path.relpath(dest, os.path.join(PROJECT_ROOT, "static"))
            return True, rel.replace("\\", "/")
        except Exception:
            # fallback to google
            pass

    # Google Charts fallback (no need to download)
    # Encode value for URL
    import urllib.parse
    v = urllib.parse.quote_plus(value)
    url = f"https://chart.googleapis.com/chart?cht=qr&chs=200x200&chl={v}&chld=L|1"
    return False, url


# ----------------------------
# Routes
# ----------------------------

@incident_report_bp.route("/")
def report_list():
    """List all incident reports."""
    df = read_excel()
    records = df.to_dict(orient="records") if not df.empty else []
    # optionally show latest first
    records = sorted(records, key=lambda r: r.get("Created_At", ""), reverse=True)
    return render_template("incident_report_list.html", records=records)


@incident_report_bp.route("/new-report", methods=["GET", "POST"])
def new_report():
    """Create a new incident report."""
    if request.method == "POST":
        form = request.form
        nid = make_id()
        now = datetime.utcnow().isoformat()
        report_number = make_report_number()
        version = 1

        rec = {
            "ID": nid,
            "Report_Number": report_number,
            "Version": version,
            "Incident_Date": form.get("Incident_Date", ""),
            "Incident_Time": form.get("Incident_Time", ""),
            "Reported_By": form.get("Reported_By", ""),
            "Department": form.get("Department", ""),
            "Location": form.get("Location", ""),
            "Incident_Type": form.get("Incident_Type", ""),
            "Immediate_Action": form.get("Immediate_Action", ""),
            "Injury_Severity": form.get("Injury_Severity", ""),
            "Description": form.get("Description", ""),
            "Affected_Persons": "",  # legacy
            "Affected_Persons_Details": "[]",
            "Sequence_of_Events": "[]",
            "Contributing_Factors": form.get("Contributing_Factors", ""),
            "Root_Cause": form.get("Root_Cause", ""),
            "Findings": form.get("Findings", ""),
            "Risk_Level": form.get("Risk_Level", ""),
            "Media_Interest": form.get("Media_Interest", ""),
            "Reputational_Risk": form.get("Reputational_Risk", ""),
            "Corrective_Actions": "[]",
            "Supervisor_Name": form.get("Supervisor_Name", ""),
            "Supervisor_Date": form.get("Supervisor_Date", ""),
            "HSO_Name": form.get("HSO_Name", ""),
            "HSO_Date": form.get("HSO_Date", ""),
            "Manager_Name": form.get("Manager_Name", ""),
            "Manager_Date": form.get("Manager_Date", ""),
            "Approvals": "[]",
            "Photos": "",
            "QR_Path": "",
            "Created_At": now,
            "Updated_At": now
        }

        # Affected persons (dynamic)
        affected = []
        i = 1
        while True:
            name = form.get(f"person_name_{i}")
            if not name:
                break
            # collect extended fields
            p = {
                "name": name.strip(),
                "emp_id": form.get(f"person_empid_{i}", "").strip(),
                "sex": form.get(f"person_sex_{i}", "").strip(),
                "age": form.get(f"person_age_{i}", "").strip(),
                "years_service": form.get(f"person_service_{i}", "").strip(),
                "role": form.get(f"person_role_{i}", "").strip(),
                "injury": form.get(f"person_injury_{i}", "").strip()
            }
            affected.append(p)
            i += 1
        rec["Affected_Persons_Details"] = json.dumps(affected, ensure_ascii=False)

        # Sequence of events (dynamic)
        events = []
        j = 1
        while True:
            date = form.get(f"event_date_{j}")
            details = form.get(f"event_details_{j}")
            if not date and not details:
                break
            events.append({
                "date": date or "",
                "time": form.get(f"event_time_{j}", ""),
                "details": details or ""
            })
            j += 1
        rec["Sequence_of_Events"] = json.dumps(events, ensure_ascii=False)

        # Corrective actions (collected via indices or default 1)
        actions = []
        idxs = form.getlist("action_item_index") or []
        if not idxs:
            # try simple 1
            if form.get("action_item_1"):
                idxs = ["1"]
        for idx in idxs:
            ai = form.get(f"action_item_{idx}", "").strip()
            if not ai:
                continue
            actions.append({
                "action": ai,
                "responsible": form.get(f"action_resp_{idx}", "").strip(),
                "due": form.get(f"action_due_{idx}", "").strip(),
                "status": form.get(f"action_status_{idx}", "Open").strip()
            })
        rec["Corrective_Actions"] = json.dumps(actions, ensure_ascii=False)

        # Photos
        files = request.files.getlist("photos") or []
        saved = save_uploaded_photos(files, nid)
        if saved:
            rec["Photos"] = ";".join(saved)

        # QR (pointing to view URL)
        host = request.host_url.rstrip("/")
        view_url = f"{host}{url_for('incident_report.view_report', id=nid).lstrip('/')}"
        is_local, qr_path_or_url = generate_qr_image(view_url, filename=f"qr_{nid}.png")
        if is_local:
            # store static-relative path so templates can call url_for
            rec["QR_Path"] = qr_path_or_url  # e.g. 'safety_reports/qrcodes/qr_xxx.png' relative to static/
        else:
            rec["QR_Path"] = qr_path_or_url  # full URL

        # Save record
        df = read_excel()
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True, sort=False)
        write_excel_atomic(df)

        flash("Incident saved.", "success")
        return redirect(url_for("incident_report.view_report", id=nid))

    # GET: show empty form
    return render_template("incident_report_form.html", data={})


@incident_report_bp.route("/<id>")
def view_report(id):
    """Show the report in HTML (and pass full parsed JSON structures to template)."""
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # parse JSON fields safely
    def _safe_parse(v):
        if not v:
            return []
        if isinstance(v, (list, dict)):
            return v
        try:
            return ast.literal_eval(v)
        except Exception:
            try:
                return json.loads(v)
            except Exception:
                return []

    rec["Affected_Persons_Details"] = _safe_parse(rec.get("Affected_Persons_Details", "[]"))
    rec["Sequence_of_Events"] = _safe_parse(rec.get("Sequence_of_Events", "[]"))
    rec["Corrective_Actions"] = _safe_parse(rec.get("Corrective_Actions", "[]"))
    rec["Approvals"] = _safe_parse(rec.get("Approvals", "[]"))

    # prevent 30+ empty rows
    rec["Affected_Persons"] = []

    # Handle QR_Path resolution: if QR_Path is local relative to static folder, construct url_for path in template
    return render_template("incident_report_pdf.html", rec=rec, for_pdf=False)


@incident_report_bp.route("/<id>/edit", methods=["GET", "POST"])
def edit_report(id):
    df = read_excel()
    idx_list = df.index[df["ID"] == id].tolist()
    if not idx_list:
        abort(404)
    idx = idx_list[0]

    if request.method == "POST":
        form = request.form
        rec = df.loc[idx].to_dict()

        # update simple fields
        simple_fields = [
            "Incident_Date", "Incident_Time", "Reported_By", "Department",
            "Location", "Incident_Type", "Immediate_Action", "Injury_Severity",
            "Description", "Contributing_Factors", "Root_Cause", "Findings",
            "Risk_Level", "Media_Interest", "Reputational_Risk",
            "Supervisor_Name", "Supervisor_Date", "HSO_Name", "HSO_Date",
            "Manager_Name", "Manager_Date"
        ]
        for field in simple_fields:
            rec[field] = form.get(field, "").strip()

        # ------------------------------------------
        # AFFECTED PERSONS
        # ------------------------------------------
        affected = []
        i = 1
        while True:
            prefix = f"person_name_{i}"
            name = form.get(prefix)
            if not name:
                break

            affected.append({
                "name": name.strip(),
                "emp_id": form.get(f"person_empid_{i}", "").strip(),
                "sex": form.get(f"person_sex_{i}", "").strip(),
                "age": form.get(f"person_age_{i}", "").strip(),
                "years_service": form.get(f"person_service_{i}", "").strip(),
                "role": form.get(f"person_role_{i}", "").strip(),
                "injury": form.get(f"person_injury_{i}", "").strip()
            })
            i += 1

        rec["Affected_Persons_Details"] = json.dumps(affected, ensure_ascii=False)

        # ------------------------------------------
        # SEQUENCE OF EVENTS
        # ------------------------------------------
        events = []
        j = 1
        while True:
            date = form.get(f"event_date_{j}")
            time = form.get(f"event_time_{j}")
            details = form.get(f"event_details_{j}")

            # stop only when ALL are empty
            if not date and not time and not details:
                break

            events.append({
                "date": date or "",
                "time": time or "",
                "details": details or ""
            })
            j += 1

        rec["Sequence_of_Events"] = json.dumps(events, ensure_ascii=False)

        # ------------------------------------------
        # CORRECTIVE ACTIONS
        # ------------------------------------------
        actions = []

        # -- FIX: during edit, we now get ALL indexes properly --
        index_list = form.getlist("action_item_index")

        for idx_i in index_list:
            ai = form.get(f"action_item_{idx_i}", "").strip()
            if not ai:
                continue

            actions.append({
                "action": ai,
                "responsible": form.get(f"action_resp_{idx_i}", "").strip(),
                "due": form.get(f"action_due_{idx_i}", "").strip(),
                "status": form.get(f"action_status_{idx_i}", "").strip()
            })

        rec["Corrective_Actions"] = json.dumps(actions, ensure_ascii=False)

        # ------------------------------------------
        # Photos (append)
        # ------------------------------------------
        files = request.files.getlist("photos")
        saved = save_uploaded_photos(files, id)
        if saved:
            existing = rec.get("Photos", "")
            existing_list = existing.split(";") if existing else []
            rec["Photos"] = ";".join(existing_list + saved)

        # bump version
        try:
            rec["Version"] = int(rec.get("Version", 1)) + 1
        except:
            rec["Version"] = 1

        rec["Updated_At"] = datetime.utcnow().isoformat()
        for k, v in rec.items():
            df.at[idx, k] = v

        write_excel_atomic(df)
        flash("Report updated.", "success")
        return redirect(url_for("incident_report.view_report", id=id))

    # -----------------------------------------------------
    # GET request → Preload JSON fields for the edit form
    # -----------------------------------------------------
    rec = df.loc[idx].to_dict()

    def parse_json(v):
        if not v:
            return []
        try:
            return json.loads(v)
        except:
            try:
                return ast.literal_eval(v)
            except:
                return []

    rec["Affected_Persons_Details"] = parse_json(rec.get("Affected_Persons_Details", "[]"))
    rec["Sequence_of_Events"] = parse_json(rec.get("Sequence_of_Events", "[]"))
    rec["Corrective_Actions"] = parse_json(rec.get("Corrective_Actions", "[]"))

    # VERY IMPORTANT:
    # Pass index numbers for the form to rebuild correct inputs
    rec["Persons_Count"] = len(rec["Affected_Persons_Details"])
    rec["Events_Count"] = len(rec["Sequence_of_Events"])
    rec["Actions_Count"] = len(rec["Corrective_Actions"])

    return render_template("incident_report_form.html", data=rec, editing=True)

@incident_report_bp.route("/<id>/export")
def export_pdf(id):
    """Export a report to PDF (uses wkhtmltopdf via pdfkit)."""
    if not pdf_config:
        abort(500, "PDF export not configured (wkhtmltopdf not found)")

    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)
    rec = row.iloc[0].to_dict()

    # parse JSON fields for template
    def _safe_parse(v):
        if not v:
            return []
        if isinstance(v, (list, dict)):
            return v
        try:
            return ast.literal_eval(v)
        except Exception:
            try:
                return json.loads(v)
            except Exception:
                return []

    rec["Affected_Persons_Details"] = _safe_parse(rec.get("Affected_Persons_Details", "[]"))
    rec["Sequence_of_Events"] = _safe_parse(rec.get("Sequence_of_Events", "[]"))
    rec["Corrective_Actions"] = _safe_parse(rec.get("Corrective_Actions", "[]"))
    rec["Approvals"] = _safe_parse(rec.get("Approvals", "[]"))

    # prevent empty loops
    rec["Affected_Persons"] = []

    html = render_template("incident_report_pdf.html", rec=rec, for_pdf=True)

    import pdfkit
    pdf_bytes = pdfkit.from_string(html, False, configuration=pdf_config)

    filename = f"{rec.get('Report_Number','report')}_v{rec.get('Version',1)}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


@incident_report_bp.route("/<id>/approve", methods=["POST"])
def approve_report(id):
    """
    Simple approval endpoint. Expects form fields:
      approver_role (Supervisor/HSO/Manager),
      approver_name,
      action (approve/reject),
      notes
    """
    df = read_excel()
    idx_list = df.index[df["ID"] == id].tolist()
    if not idx_list:
        abort(404)
    idx = idx_list[0]

    form = request.form
    role = form.get("approver_role", "")
    name = form.get("approver_name", "")
    action = form.get("action", "approve")
    notes = form.get("notes", "")

    if not role or not name:
        flash("Approver role and name required.", "warning")
        return redirect(url_for("incident_report.view_report", id=id))

    approvals_raw = df.at[idx, "Approvals"] if pd.notna(df.at[idx, "Approvals"]) else "[]"
    try:
        approvals = ast.literal_eval(approvals_raw)
    except Exception:
        try:
            approvals = json.loads(approvals_raw)
        except Exception:
            approvals = []

    record = {
        "role": role,
        "name": name,
        "action": action,
        "notes": notes,
        "when": datetime.utcnow().isoformat()
    }
    approvals.append(record)
    df.at[idx, "Approvals"] = json.dumps(approvals, ensure_ascii=False)
    df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()
    write_excel_atomic(df)

    flash("Approval recorded.", "success")
    return redirect(url_for("incident_report.view_report", id=id))

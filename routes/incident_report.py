# -------------------------------------------------------------
# incident_report.py  — CLEAN FULL WORKING VERSION (Part 1/3)
# -------------------------------------------------------------

import os
import uuid
import io
import ast
import json
import shutil
import platform
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, abort, current_app
)
from werkzeug.utils import secure_filename

# -----------------------------
# QR Code (optional local lib)
# -----------------------------
try:
    import qrcode
    QR_LIB = "qrcode"
except Exception:
    QR_LIB = "google"
    qrcode = None

# -----------------------------
# WKHTMLTOPDF CONFIG
# -----------------------------
if platform.system() == "Windows":
    WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if not os.path.exists(WKHTMLTOPDF_PATH):
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

# -----------------------------
# BLUEPRINT
# -----------------------------
incident_report_bp = Blueprint(
    "incident_report",
    __name__,
    template_folder="../templates/safety",
    url_prefix="/safety/incidents"
)

# -----------------------------
# PATHS
# -----------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "static", "safety_reports")
QR_DIR = os.path.join(UPLOAD_DIR, "qrcodes")
EXCEL_FILE = os.path.join(DATA_DIR, "incidents_full_report.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "svg"}


# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------
def ensure_file():
    """Create Excel file if missing."""
    if not os.path.exists(EXCEL_FILE):
        cols = [
            "ID", "Report_Number", "Version",
            "Incident_Date", "Incident_Time",
            "Reported_By", "Department", "Location",
            "Incident_Type", "Immediate_Action", "Injury_Severity",
            "Description",

            "Affected_Persons",
            "Affected_Persons_Details",  # JSON
            "Sequence_of_Events",         # JSON
            "Contributing_Factors",
            "Root_Cause",
            "Findings",
            "Risk_Level",
            "Media_Interest",
            "Reputational_Risk",
            "Corrective_Actions",         # JSON

            "Supervisor_Name", "Supervisor_Date",
            "HSO_Name", "HSO_Date",
            "Manager_Name", "Manager_Date",

            "Investigator", "Investigation_Date",
            "Prepared_By", "Prepared_Date",

            "Approvals",                  # JSON
            "Photos",                     # semicolon list
            "QR_Path",

            "Created_At",
            "Updated_At"
        ]
        pd.DataFrame(columns=cols).to_excel(EXCEL_FILE, index=False)


def ensure_columns():
    """Ensure all required columns exist."""
    required = [
        "ID", "Report_Number", "Version",
        "Incident_Date", "Incident_Time",
        "Reported_By", "Department", "Location",
        "Incident_Type", "Immediate_Action", "Injury_Severity",
        "Description",
        "Affected_Persons",
        "Affected_Persons_Details",
        "Sequence_of_Events",
        "Contributing_Factors", "Root_Cause", "Findings",
        "Risk_Level", "Media_Interest", "Reputational_Risk",
        "Corrective_Actions",
        "Supervisor_Name", "Supervisor_Date",
        "HSO_Name", "HSO_Date",
        "Manager_Name", "Manager_Date",
        "Investigator", "Investigation_Date",
        "Prepared_By", "Prepared_Date",
        "Approvals",
        "Photos", "QR_Path",
        "Created_At", "Updated_At"
    ]

    df = pd.read_excel(EXCEL_FILE).fillna("")
    updated = False

    for c in required:
        if c not in df.columns:
            df[c] = ""
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
    today = datetime.utcnow().strftime("%Y%m%d")
    df = read_excel()
    count_today = len(df[df["Created_At"].str.startswith(today)])
    return f"RPT-{today}-{count_today + 1:04d}"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def save_uploaded_photos(files, prefix):
    saved = []
    for f in files or []:
        if f and f.filename and allowed_file(f.filename):
            fn = secure_filename(f.filename)
            unique = f"{prefix}_{uuid.uuid4().hex}_{fn}"
            f.save(os.path.join(UPLOAD_DIR, unique))
            saved.append(unique)
    return saved

def generate_qr_image(value, filename=None):
    """
    Always try to save a QR code into:
        static/safety_reports/qrcodes/
    Falls back to Google QR URL only if saving fails.
    """
    import urllib.parse

    # ensure path exists
    os.makedirs(QR_DIR, exist_ok=True)

    if not filename:
        filename = f"qr_{uuid.uuid4().hex}.png"

    dest = os.path.join(QR_DIR, filename)

    # Try local QR generation
    try:
        if QR_LIB == "qrcode" and qrcode is not None:
            img = qrcode.make(value)
            img.save(dest)

            # convert to static-relative path
            rel = os.path.relpath(dest, os.path.join(PROJECT_ROOT, "static"))
            rel = rel.replace("\\", "/")

            print("QR SAVED:", rel, " -> ", dest)
            return True, rel

    except Exception as e:
        print("QR GENERATION ERROR:", e)

    # Fallback (Google)
    print("⚠️ Falling back to GOOGLE QR")
    v = urllib.parse.quote_plus(value)
    url = f"https://chart.googleapis.com/chart?cht=qr&chs=200x200&chl={v}&chld=L|1"
    return False, url


# -------------------------------------------------------------
# ROUTES — PART 2/3
# -------------------------------------------------------------

# -------------------------------------------------------------
# LIST REPORTS
# -------------------------------------------------------------
@incident_report_bp.route("/")
def report_list():
    df = read_excel()
    records = df.to_dict(orient="records") if not df.empty else []
    records = sorted(records, key=lambda r: r.get("Created_At", ""), reverse=True)
    return render_template("incident_report_list.html", records=records)


# -------------------------------------------------------------
# NEW REPORT
# -------------------------------------------------------------
@incident_report_bp.route("/new-report", methods=["GET", "POST"])
def new_report():
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

            # Extended signatures
            "Investigator": form.get("Investigator", ""),
            "Investigation_Date": form.get("Investigation_Date", ""),
            "Prepared_By": form.get("Prepared_By", ""),
            "Prepared_Date": form.get("Prepared_Date", ""),

            "Contributing_Factors": form.get("Contributing_Factors", ""),
            "Root_Cause": form.get("Root_Cause", ""),
            "Findings": form.get("Findings", ""),
            "Risk_Level": form.get("Risk_Level", ""),
            "Media_Interest": form.get("Media_Interest", ""),
            "Reputational_Risk": form.get("Reputational_Risk", ""),

            "Supervisor_Name": form.get("Supervisor_Name", ""),
            "Supervisor_Date": form.get("Supervisor_Date", ""),
            "HSO_Name": form.get("HSO_Name", ""),
            "HSO_Date": form.get("HSO_Date", ""),
            "Manager_Name": form.get("Manager_Name", ""),
            "Manager_Date": form.get("Manager_Date", ""),

            # JSON fields
            "Affected_Persons": "",
            "Affected_Persons_Details": "[]",
            "Sequence_of_Events": "[]",
            "Corrective_Actions": "[]",
            "Approvals": "[]",

            "Photos": "",
            "QR_Path": "",

            "Created_At": now,
            "Updated_At": now
        }

        # ---------------------------
        # AFFECTED PERSONS (Dynamic)
        # ---------------------------
        persons = []
        i = 1
        while True:
            name = form.get(f"person_name_{i}")
            if not name:
                break

            persons.append({
                "name": name.strip(),
                "emp_id": form.get(f"person_empid_{i}", "").strip(),
                "sex": form.get(f"person_sex_{i}", "").strip(),
                "age": form.get(f"person_age_{i}", "").strip(),
                "years_service": form.get(f"person_service_{i}", "").strip(),
                "role": form.get(f"person_role_{i}", "").strip(),
                "injury": form.get(f"person_injury_{i}", "").strip(),
            })
            i += 1

        rec["Affected_Persons_Details"] = json.dumps(persons, ensure_ascii=False)

        # ---------------------------
        # SEQUENCE OF EVENTS
        # ---------------------------
        events = []
        j = 1
        while True:
            date = form.get(f"event_date_{j}")
            time = form.get(f"event_time_{j}")
            details = form.get(f"event_details_{j}")

            if not date and not time and not details:
                break

            events.append({
                "date": date or "",
                "time": time or "",
                "details": details or "",
            })
            j += 1

        rec["Sequence_of_Events"] = json.dumps(events, ensure_ascii=False)

        # ---------------------------
        # CORRECTIVE ACTIONS
        # ---------------------------
        actions = []
        indexes = form.getlist("action_item_index")
        for idx in indexes:
            info = form.get(f"action_item_{idx}", "").strip()
            if not info:
                continue

            actions.append({
                "action": info,
                "responsible": form.get(f"action_resp_{idx}", "").strip(),
                "due": form.get(f"action_due_{idx}", "").strip(),
                "status": form.get(f"action_status_{idx}", "Open").strip(),
            })

        rec["Corrective_Actions"] = json.dumps(actions, ensure_ascii=False)

        # ---------------------------
        # PHOTOS
        # ---------------------------
        files = request.files.getlist("photos")
        saved = save_uploaded_photos(files, nid)
        if saved:
            rec["Photos"] = ";".join(saved)

        # ---------------------------
        # QR CODE
        # ---------------------------
        host = request.host_url.rstrip("/")
        view_url = f"{host}{url_for('incident_report.view_report', id=nid)}"
        is_local, qr_path_or_url = generate_qr_image(view_url, filename=f"qr_{nid}.png")

        if is_local:
            rec["QR_Path"] = qr_path_or_url      # static-relative path
        else:
            rec["QR_Path"] = qr_path_or_url      # full URL

        # ---------------------------
        # SAVE
        # ---------------------------
        df = read_excel()
        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        write_excel_atomic(df)

        flash("Incident report created.", "success")
        return redirect(url_for("incident_report.view_report", id=nid))

    return render_template("incident_report_form.html", data={}, editing=False)


# -------------------------------------------------------------
# VIEW REPORT
# -------------------------------------------------------------
@incident_report_bp.route("/<id>")
def view_report(id):
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # -------- Parse JSON fields --------
    def parse(v):
        if not v:
            return []
        try:
            return json.loads(v)
        except:
            try:
                return ast.literal_eval(v)
            except:
                return []

    rec["Affected_Persons_Details"] = parse(rec.get("Affected_Persons_Details"))
    rec["Sequence_of_Events"] = parse(rec.get("Sequence_of_Events"))
    rec["Corrective_Actions"] = parse(rec.get("Corrective_Actions"))
    rec["Approvals"] = parse(rec.get("Approvals"))

    # Prevent empty legacy field
    rec["Affected_Persons"] = []

    return render_template("incident_report_pdf.html", rec=rec, for_pdf=False)


# -------------------------------------------------------------
# EDIT REPORT
# -------------------------------------------------------------
@incident_report_bp.route("/<id>/edit", methods=["GET", "POST"])
def edit_report(id):
    df = read_excel()
    rows = df.index[df["ID"] == id].tolist()
    if not rows:
        abort(404)
    idx = rows[0]

    if request.method == "POST":
        form = request.form
        rec = df.loc[idx].to_dict()

        # Simple fields
        fields = [
            "Incident_Date", "Incident_Time", "Reported_By", "Department",
            "Location", "Incident_Type", "Immediate_Action", "Injury_Severity",
            "Description", "Contributing_Factors", "Root_Cause", "Findings",
            "Risk_Level", "Media_Interest", "Reputational_Risk",
            "Supervisor_Name", "Supervisor_Date",
            "HSO_Name", "HSO_Date",
            "Manager_Name", "Manager_Date",
            "Investigator", "Investigation_Date",
            "Prepared_By", "Prepared_Date"
        ]
        for f in fields:
            rec[f] = form.get(f, "").strip()

        # Affected persons
        persons = []
        i = 1
        while True:
            name = form.get(f"person_name_{i}")
            if not name:
                break
            persons.append({
                "name": name.strip(),
                "emp_id": form.get(f"person_empid_{i}", "").strip(),
                "sex": form.get(f"person_sex_{i}", "").strip(),
                "age": form.get(f"person_age_{i}", "").strip(),
                "years_service": form.get(f"person_service_{i}", "").strip(),
                "role": form.get(f"person_role_{i}", "").strip(),
                "injury": form.get(f"person_injury_{i}", "").strip()
            })
            i += 1

        rec["Affected_Persons_Details"] = json.dumps(persons, ensure_ascii=False)

        # Sequence of events
        events = []
        j = 1
        while True:
            date = form.get(f"event_date_{j}")
            time = form.get(f"event_time_{j}")
            details = form.get(f"event_details_{j}")

            if not date and not time and not details:
                break

            events.append({
                "date": date or "",
                "time": time or "",
                "details": details or ""
            })
            j += 1

        rec["Sequence_of_Events"] = json.dumps(events, ensure_ascii=False)

        # Corrective actions
        actions = []
        indexes = form.getlist("action_item_index")
        for idx_i in indexes:
            info = form.get(f"action_item_{idx_i}", "").strip()
            if not info:
                continue
            actions.append({
                "action": info,
                "responsible": form.get(f"action_resp_{idx_i}", "").strip(),
                "due": form.get(f"action_due_{idx_i}", "").strip(),
                "status": form.get(f"action_status_{idx_i}", "").strip(),
            })

        rec["Corrective_Actions"] = json.dumps(actions, ensure_ascii=False)

        # Photos (append)
        files = request.files.getlist("photos")
        saved = save_uploaded_photos(files, id)
        if saved:
            existing = rec.get("Photos", "")
            existing_list = existing.split(";") if existing else []
            rec["Photos"] = ";".join(existing_list + saved)

        # Version bump
        try:
            rec["Version"] = int(rec.get("Version", 1)) + 1
        except:
            rec["Version"] = 1

        rec["Updated_At"] = datetime.utcnow().isoformat()

        # Save
        for k, v in rec.items():
            df.at[idx, k] = v

        write_excel_atomic(df)
        flash("Report updated.", "success")
        return redirect(url_for("incident_report.view_report", id=id))

    # GET (editing)
    rec = df.loc[idx].to_dict()

    def parse(v):
        if not v:
            return []
        try:
            return json.loads(v)
        except:
            try:
                return ast.literal_eval(v)
            except:
                return []

    rec["Affected_Persons_Details"] = parse(rec.get("Affected_Persons_Details"))
    rec["Sequence_of_Events"] = parse(rec.get("Sequence_of_Events"))
    rec["Corrective_Actions"] = parse(rec.get("Corrective_Actions"))

    # counts for form
    rec["Persons_Count"] = len(rec["Affected_Persons_Details"])
    rec["Events_Count"] = len(rec["Sequence_of_Events"])
    rec["Actions_Count"] = len(rec["Corrective_Actions"])

    return render_template("incident_report_form.html", data=rec, editing=True)

# -------------------------------------------------------------
# ROUTES — PART 3/3 (Export PDF + Approvals)
# -------------------------------------------------------------

def _safe_parse_list_field(v):
    """Robustly parse a JSON/list field stored as string in Excel."""
    if not v:
        return []
    if isinstance(v, (list, tuple)):
        return v
    try:
        return json.loads(v)
    except Exception:
        try:
            return ast.literal_eval(v)
        except Exception:
            return []


def _make_absolute_static(host, relative_path):
    """Return absolute URL for a static file (works on Windows/Unix path separators)."""
    if not relative_path:
        return ""
    # If already absolute URL, return as-is
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return relative_path
    # url_for requires a path relative to static, so ensure we don't double prefix
    return f"{host}{url_for('static', filename=relative_path)}"


def _generate_pdf_bytes(rec):
    """Render template to HTML and convert to PDF bytes (throws if pdfkit not configured)."""
    if not pdf_config:
        raise RuntimeError("PDF export not configured (wkhtmltopdf not found)")

    html = render_template("incident_report_pdf.html", rec=rec, for_pdf=True)
    import pdfkit
    return pdfkit.from_string(html, False, configuration=pdf_config)


# -----------------------
# EXPORT: primary endpoint (absolute URLs fixed for wkhtmltopdf)
# -----------------------
@incident_report_bp.route("/report/<id>/pdf", endpoint="export_pdf")
def export_pdf(id):
    """
    Export the incident report to PDF.
    Uses absolute URLs for images (wkhtmltopdf requires them).
    """
    df = read_excel()
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)
    rec = row.iloc[0].to_dict()

    # parse list fields
    rec["Affected_Persons_Details"] = _safe_parse_list_field(rec.get("Affected_Persons_Details"))
    rec["Sequence_of_Events"] = _safe_parse_list_field(rec.get("Sequence_of_Events"))
    rec["Corrective_Actions"] = _safe_parse_list_field(rec.get("Corrective_Actions"))
    rec["Approvals"] = _safe_parse_list_field(rec.get("Approvals"))

    # prepare absolute URLs for photos and QR (wkhtmltopdf needs full URLs)
    host = request.host_url.rstrip("/")

    # Photos -> absolute urls list available in template as rec.Photos_ForPDF
    photos_for_pdf = []
    if rec.get("Photos"):
        for p in str(rec.get("Photos")).split(";"):
            if not p:
                continue
            photos_for_pdf.append(_make_absolute_static(host, os.path.join("safety_reports", p)))
    rec["Photos_ForPDF"] = photos_for_pdf

    # QR_Path -> ensure absolute if local
    qr = rec.get("QR_Path", "")
    if qr:
        if qr.startswith("http://") or qr.startswith("https://"):
            rec["QR_Path"] = qr
        else:
            # QR_Path stored as static-relative (e.g. 'safety_reports/qrcodes/qr_xxx.png')
            rec["QR_Path"] = _make_absolute_static(host, qr)

    # Also provide a helpful 'host' value to templates if desired
    rec["__host"] = host

    # Generate PDF
    try:
        pdf_bytes = _generate_pdf_bytes(rec)
    except Exception as e:
        # bubble up a clearer message for debugging
        current_app.logger.exception("PDF generation failed")
        abort(500, f"PDF generation failed: {e}")

    filename = f"{rec.get('Report_Number','report')}_v{rec.get('Version',1)}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# -----------------------
# EXPORT ALIAS (some templates / links used earlier reference 'export_report')
# -----------------------
@incident_report_bp.route("/<id>/export", endpoint="export_report")
def export_report(id):
    """
    Alias endpoint for exporting. Calls the main export_pdf implementation.
    Keeps backward compatibility with templates linking to 'export_report'.
    """
    # Delegate to export_pdf (same behaviour)
    return export_pdf(id)


# -----------------------
# APPROVALS
# -----------------------
@incident_report_bp.route("/<id>/approve", methods=["POST"])
def approve_report(id):
    """
    Record an approval action (Supervisor/HSO/Manager).
    Expects form fields: approver_role, approver_name, action (approve/reject), notes
    """
    df = read_excel()
    idx_list = df.index[df["ID"] == id].tolist()
    if not idx_list:
        abort(404)
    idx = idx_list[0]

    form = request.form
    role = form.get("approver_role", "").strip()
    name = form.get("approver_name", "").strip()
    action = form.get("action", "approve").strip()
    notes = form.get("notes", "").strip()

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

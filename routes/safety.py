# routes/safety.py
import os
import uuid
from datetime import datetime
import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, abort
)
from werkzeug.utils import secure_filename

safety_bp = Blueprint(
    "safety",
    __name__,
    template_folder="../templates/safety",
    url_prefix="/safety"
)

# ---------------------
# Config / Paths
# ---------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "static", "safety_uploads")
CSS_DIR = os.path.join(PROJECT_ROOT, "static", "safety")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

# Excel files
INCIDENT_FILE = os.path.join(DATA_DIR, "safety_incidents.xlsx")
CORRECTIVE_FILE = os.path.join(DATA_DIR, "safety_corrective.xlsx")
TRAINING_FILE = os.path.join(DATA_DIR, "safety_training.xlsx")
TOOLBOX_FILE = os.path.join(DATA_DIR, "safety_toolbox.xlsx")
CHECKLIST_FILE = os.path.join(DATA_DIR, "safety_checklists.xlsx")

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}

# ---------------------
# Helpers: ensure files, read/write
# ---------------------
def ensure_files():
    if not os.path.exists(INCIDENT_FILE):
        df = pd.DataFrame(columns=[
            "ID", "Date", "Time", "Type", "Severity", "Location",
            "Reported_By", "Role", "Description", "Actions_Taken",
            "Assigned_To", "Status", "Photo", "Created_At", "Updated_At"
        ])
        df.to_excel(INCIDENT_FILE, index=False)

    if not os.path.exists(CORRECTIVE_FILE):
        df = pd.DataFrame(columns=[
            "ID", "Incident_ID", "Action", "Status", "Assigned_To", "Notes", "Created_At", "Updated_At"
        ])
        df.to_excel(CORRECTIVE_FILE, index=False)

    if not os.path.exists(TRAINING_FILE):
        df = pd.DataFrame(columns=[
            "ID", "Date", "Employee", "Topic", "Trainer", "Expiry", "Notes", "Created_At"
        ])
        df.to_excel(TRAINING_FILE, index=False)

    if not os.path.exists(TOOLBOX_FILE):
        df = pd.DataFrame(columns=[
            "ID", "Date", "Topic", "Trainer", "Participants", "Notes", "Created_At"
        ])
        df.to_excel(TOOLBOX_FILE, index=False)

    if not os.path.exists(CHECKLIST_FILE):
        df = pd.DataFrame(columns=[
            "ID", "Date", "Checklist_Name", "Performed_By", "Notes", "Created_At"
        ])
        df.to_excel(CHECKLIST_FILE, index=False)

def read_excel(path):
    ensure_files()
    try:
        return pd.read_excel(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()

def write_excel_atomic(path, df):
    tmp = path + ".tmp"
    df.to_excel(tmp, index=False)
    os.replace(tmp, path)

def make_id():
    return uuid.uuid4().hex

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT

# ---------------------
# DASHBOARD
# ---------------------
@safety_bp.route("/")
def dashboard():
    # Ensure all Excel files exist
    ensure_files()

    # Read your Excel files
    inc_df = read_excel(INCIDENT_FILE)
    corr_df = read_excel(CORRECTIVE_FILE)
    train_df = read_excel(TRAINING_FILE)
    toolbox_df = read_excel(TOOLBOX_FILE)

    # Optional: define CHECKLIST_FILE if you have checklists
    CHECKLIST_FILE = os.path.join(DATA_DIR, "safety_checklists.xlsx")
    if not os.path.exists(CHECKLIST_FILE):
        # create empty checklists file with columns
        pd.DataFrame(columns=["ID", "Date", "Title", "Completed", "Notes", "Created_At"]).to_excel(CHECKLIST_FILE, index=False)
    checklists_df = read_excel(CHECKLIST_FILE)

    # Compute totals safely
    totals = {
        "incidents": len(inc_df) if not inc_df.empty else 0,
        "corrective": len(corr_df[corr_df.get("Status","") != "Completed"]) if not corr_df.empty else 0,
        "training": len(train_df) if not train_df.empty else 0,
        "toolbox": len(toolbox_df) if not toolbox_df.empty else 0,
        "checklists": len(checklists_df) if not checklists_df.empty else 0
    }

    # Pass totals to template
    return render_template("safety/safety_dashboard.html", totals=totals)

# ---------------------
# INCIDENTS
# ---------------------
@safety_bp.route("/incidents")
def incident_list():
    df = read_excel(INCIDENT_FILE)
    records = df.to_dict(orient="records") if not df.empty else []
    return render_template("incident_list.html", incidents=records)

@safety_bp.route("/incidents/new", methods=["GET", "POST"])
def incident_add():
    if request.method == "POST":
        form = request.form
        nid = make_id()
        now = datetime.utcnow().isoformat()
        rec = {
            "ID": nid,
            "Date": form.get("Date", datetime.utcnow().date().isoformat()),
            "Time": form.get("Time", ""),
            "Type": form.get("Type", ""),
            "Severity": form.get("Severity", ""),
            "Location": form.get("Location", ""),
            "Reported_By": form.get("Reported_By", ""),
            "Role": form.get("Role", ""),
            "Description": form.get("Description", ""),
            "Actions_Taken": form.get("Actions_Taken", ""),
            "Assigned_To": form.get("Assigned_To", ""),
            "Status": form.get("Status", "Open"),
            "Photo": "",
            "Created_At": now,
            "Updated_At": now
        }

        files = request.files.getlist("Photo") or []
        saved = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                fn = secure_filename(f.filename)
                unique = f"{nid}_{uuid.uuid4().hex}_{fn}"
                path = os.path.join(UPLOAD_DIR, unique)
                f.save(path)
                saved.append(unique)
        if saved:
            rec["Photo"] = ";".join(saved)

        df = read_excel(INCIDENT_FILE)
        df = df.append(rec, ignore_index=True)
        write_excel_atomic(INCIDENT_FILE, df)
        flash("Incident added.", "success")
        return redirect(url_for("safety.incident_list"))

    return render_template("incident_form.html", action="Add", data={})

@safety_bp.route("/incidents/<id>")
def incident_view(id):
    df = read_excel(INCIDENT_FILE)
    row = df[df["ID"] == id]
    if row.empty:
        abort(404)
    row = row.iloc[0].to_dict()
    return render_template("incident_view.html", row=row)

@safety_bp.route("/incidents/<id>/edit", methods=["GET", "POST"])
def incident_edit(id):
    df = read_excel(INCIDENT_FILE)
    idx = df.index[df["ID"] == id].tolist()
    if not idx:
        abort(404)
    idx = idx[0]

    if request.method == "POST":
        form = request.form
        for field in ["Date","Time","Type","Severity","Location","Reported_By","Role","Description","Actions_Taken","Assigned_To","Status"]:
            df.at[idx, field] = form.get(field, df.at[idx, field])
        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()

        files = request.files.getlist("Photo") or []
        existing = df.at[idx, "Photo"] if pd.notna(df.at[idx, "Photo"]) else ""
        photos = existing.split(";") if existing else []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                fn = secure_filename(f.filename)
                unique = f"{id}_{uuid.uuid4().hex}_{fn}"
                path = os.path.join(UPLOAD_DIR, unique)
                f.save(path)
                photos.append(unique)
        df.at[idx, "Photo"] = ";".join([p for p in photos if p])

        write_excel_atomic(INCIDENT_FILE, df)
        flash("Incident updated.", "success")
        return redirect(url_for("safety.incident_view", id=id))

    row = df.loc[idx].to_dict()
    return render_template("incident_form.html", action="Edit", data=row)

@safety_bp.route("/incidents/<id>/delete")
def incident_delete(id):
    df = read_excel(INCIDENT_FILE)
    if id not in df["ID"].values:
        abort(404)
    row = df[df["ID"] == id].iloc[0]
    photos = row.get("Photo", "")
    if photos:
        for p in photos.split(";"):
            path = os.path.join(UPLOAD_DIR, p)
            if os.path.exists(path):
                os.remove(path)
    df = df[df["ID"] != id]
    write_excel_atomic(INCIDENT_FILE, df)
    flash("Incident deleted.", "info")
    return redirect(url_for("safety.incident_list"))

# ---------------------
# CORRECTIVE ACTIONS
# ---------------------
@safety_bp.route("/corrective")
def corrective_list():
    df = read_excel(CORRECTIVE_FILE)
    records = df.to_dict(orient="records") if not df.empty else []
    return render_template("corrective_list.html", corrective=records)

@safety_bp.route("/corrective/new", methods=["GET", "POST"])
def corrective_add():
    if request.method == "POST":
        form = request.form
        nid = make_id()
        now = datetime.utcnow().isoformat()
        rec = {
            "ID": nid,
            "Incident_ID": form.get("Incident_ID", ""),
            "Action": form.get("Action", ""),
            "Status": form.get("Status", "Open"),
            "Assigned_To": form.get("Assigned_To", ""),
            "Notes": form.get("Notes", ""),
            "Created_At": now,
            "Updated_At": now
        }
        df = read_excel(CORRECTIVE_FILE)
        df = df.append(rec, ignore_index=True)
        write_excel_atomic(CORRECTIVE_FILE, df)
        flash("Corrective action recorded.", "success")
        return redirect(url_for("safety.corrective_list"))

    # GET -> show empty form
    return render_template("safety/corrective_form.html", action="Add", data={})

@safety_bp.route("/corrective/<id>/edit", methods=["GET", "POST"])
def corrective_edit(id):
    df = read_excel(CORRECTIVE_FILE)
    idx = df.index[df["ID"] == id].tolist()
    if not idx:
        abort(404)
    idx = idx[0]

    if request.method == "POST":
        form = request.form
        df.at[idx, "Action"] = form.get("Action", df.at[idx, "Action"])
        df.at[idx, "Status"] = form.get("Status", df.at[idx, "Status"])
        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()
        write_excel_atomic(CORRECTIVE_FILE, df)
        flash("Corrective action updated.", "success")
        return redirect(url_for("safety.corrective_list"))

    # GET -> provide current row data
    row = df.loc[idx].to_dict()
    return render_template("safety/corrective_form.html", action="Edit", data=row)

# ---------------------
# TRAINING
# ---------------------
@safety_bp.route("/training")
def training_list():
    df = read_excel(TRAINING_FILE)
    records = df.to_dict(orient="records") if not df.empty else []
    return render_template("training_records.html", training=records)

@safety_bp.route("/training/new", methods=["GET","POST"])
def training_add():
    if request.method=="POST":
        form=request.form
        nid=make_id()
        now=datetime.utcnow().isoformat()
        rec={
            "ID":nid,
            "Date":form.get("Date",datetime.utcnow().date().isoformat()),
            "Employee":form.get("Employee",""),
            "Topic":form.get("Topic",""),
            "Trainer":form.get("Trainer",""),
            "Expiry":form.get("Expiry",""),
            "Notes":form.get("Notes",""),
            "Created_At":now
        }
        df=read_excel(TRAINING_FILE)
        df=df.append(rec,ignore_index=True)
        write_excel_atomic(TRAINING_FILE,df)
        flash("Training record saved.","success")
        return redirect(url_for("safety.training_list"))
    return render_template("training_form.html", action="Add", data={})

# ---------------------
# TOOLBOX TALKS
# ---------------------
@safety_bp.route("/toolbox")
def toolbox_list():
    df=read_excel(TOOLBOX_FILE)
    records=df.to_dict(orient="records") if not df.empty else []
    return render_template("toolbox_list.html", toolbox=records)

@safety_bp.route("/toolbox/new",methods=["GET","POST"])
def toolbox_add():
    if request.method=="POST":
        form=request.form
        nid=make_id()
        now=datetime.utcnow().isoformat()
        rec={
            "ID":nid,
            "Date":form.get("Date",datetime.utcnow().date().isoformat()),
            "Topic":form.get("Topic",""),
            "Trainer":form.get("Trainer",""),
            "Participants":form.get("Participants",""),
            "Notes":form.get("Notes",""),
            "Created_At":now
        }
        df=read_excel(TOOLBOX_FILE)
        df=df.append(rec,ignore_index=True)
        write_excel_atomic(TOOLBOX_FILE,df)
        flash("Toolbox talk saved.","success")
        return redirect(url_for("safety.toolbox_list"))
    return render_template("toolbox_form.html", action="Add", data={})

# ---------------------
# CHECKLISTS
# ---------------------
@safety_bp.route("/checklists")
def checklist_list():
    df=read_excel(CHECKLIST_FILE)
    records=df.to_dict(orient="records") if not df.empty else []
    return render_template("checklists.html", checklists=records)

@safety_bp.route("/checklists/new",methods=["GET","POST"])
def checklist_add():
    if request.method=="POST":
        form=request.form
        nid=make_id()
        now=datetime.utcnow().isoformat()
        rec={
            "ID":nid,
            "Date":form.get("Date",datetime.utcnow().date().isoformat()),
            "Checklist_Name":form.get("Checklist_Name",""),
            "Performed_By":form.get("Performed_By",""),
            "Notes":form.get("Notes",""),
            "Created_At":now
        }
        df=read_excel(CHECKLIST_FILE)
        df=df.append(rec,ignore_index=True)
        write_excel_atomic(CHECKLIST_FILE,df)
        flash("Checklist saved.","success")
        return redirect(url_for("safety.checklist"))
    return render_template("checklist_form.html", action="Add", data={})

# ---------------------
# Export helper (optional)
# ---------------------
@safety_bp.route("/incidents/export")
def incidents_export():
    df=read_excel(INCIDENT_FILE)
    outfile=os.path.join(DATA_DIR,f"safety_incidents_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx")
    df.to_excel(outfile,index=False)
    return send_file(outfile,as_attachment=True)

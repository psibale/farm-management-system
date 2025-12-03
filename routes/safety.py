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
# Paths
# ---------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "static", "safety_uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

INCIDENT_FILE = os.path.join(DATA_DIR, "safety_incidents.xlsx")
CORRECTIVE_FILE = os.path.join(DATA_DIR, "safety_corrective.xlsx")
TRAINING_FILE = os.path.join(DATA_DIR, "safety_training.xlsx")
TOOLBOX_FILE = os.path.join(DATA_DIR, "safety_toolbox.xlsx")
CHECKLIST_FILE = os.path.join(DATA_DIR, "safety_checklists.xlsx")

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}

# ---------------------
# Helpers
# ---------------------
def ensure_files():
    """Create Excel files if missing."""
    if not os.path.exists(INCIDENT_FILE):
        pd.DataFrame(columns=[
            "ID", "Date", "Time", "Type", "Severity", "Location",
            "Reported_By", "Role", "Description", "Actions_Taken",
            "Assigned_To", "Status", "Photo",
            "Created_At", "Updated_At"
        ]).to_excel(INCIDENT_FILE, index=False)

    if not os.path.exists(CORRECTIVE_FILE):
        pd.DataFrame(columns=[
            "ID", "Incident_ID", "Action", "Status",
            "Assigned_To", "Notes", "Created_At", "Updated_At"
        ]).to_excel(CORRECTIVE_FILE, index=False)

    if not os.path.exists(TRAINING_FILE):
        pd.DataFrame(columns=[
            "ID", "Date", "Employee", "Topic", "Trainer",
            "Expiry", "Notes", "Created_At"
        ]).to_excel(TRAINING_FILE, index=False)

    if not os.path.exists(TOOLBOX_FILE):
        pd.DataFrame(columns=[
            "ID", "Date", "Topic", "Facilitator",
            "Participants", "Notes", "Created_At"
        ]).to_excel(TOOLBOX_FILE, index=False)

    if not os.path.exists(CHECKLIST_FILE):
        pd.DataFrame(columns=[
            "ID", "Date", "Checklist_Name",
            "Performed_By", "Notes", "Created_At"
        ]).to_excel(CHECKLIST_FILE, index=False)


def read_excel(path):
    ensure_files()
    try:
        return pd.read_excel(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def write_excel_atomic(path, df):
    base, ext = os.path.splitext(path)
    tmp = f"{base}_tmp{ext}"
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
    ensure_files()

    inc = read_excel(INCIDENT_FILE)
    corr = read_excel(CORRECTIVE_FILE)
    train = read_excel(TRAINING_FILE)
    toolbox = read_excel(TOOLBOX_FILE)
    check = read_excel(CHECKLIST_FILE)

    totals = {
        "incidents": len(inc),
        "corrective": len(corr[corr["Status"] != "Completed"]) if not corr.empty else 0,
        "training": len(train),
        "toolbox": len(toolbox),
        "checklists": len(check),
    }

    return render_template("safety/safety_dashboard.html", totals=totals)


# ---------------------
# INCIDENTS
# ---------------------
@safety_bp.route("/incidents")
def incident_list():
    df = read_excel(INCIDENT_FILE)
    return render_template("safety/incident_list.html",
                           incidents=df.to_dict(orient="records"))


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

        # Photo uploads
        photos = []
        for f in request.files.getlist("Photo"):
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                name = f"{nid}_{uuid.uuid4().hex}_{filename}"
                f.save(os.path.join(UPLOAD_DIR, name))
                photos.append(name)

        rec["Photo"] = ";".join(photos)

        df = read_excel(INCIDENT_FILE)
        write_excel_atomic(INCIDENT_FILE,
                           pd.concat([df, pd.DataFrame([rec])], ignore_index=True))

        flash("Incident added.", "success")
        return redirect(url_for("safety.incident_list"))

    return render_template("safety/incident_form.html", action="Add", data={})


@safety_bp.route("/incidents/<id>")
def incident_view(id):
    df = read_excel(INCIDENT_FILE)
    row = df[df["ID"] == id]

    if row.empty:
        abort(404)

    rec = row.iloc[0].to_dict()

    # Load corrective actions for this incident
    corr_df = read_excel(CORRECTIVE_FILE)
    linked = corr_df[corr_df["Incident_ID"] == id].to_dict(orient="records")

    return render_template("safety/incident_view.html",
                           rec=rec,
                           corrective=linked)


@safety_bp.route("/incidents/<id>/edit", methods=["GET", "POST"])
def incident_edit(id):
    df = read_excel(INCIDENT_FILE)
    idx_list = df.index[df["ID"] == id].tolist()

    if not idx_list:
        abort(404)

    idx = idx_list[0]

    if request.method == "POST":
        form = request.form

        for field in [
            "Date", "Time", "Type", "Severity", "Location",
            "Reported_By", "Role", "Description", "Actions_Taken",
            "Assigned_To", "Status"
        ]:
            df.at[idx, field] = form.get(field, df.at[idx, field])

        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()

        # Append new photos
        existing = df.at[idx, "Photo"]
        photos = existing.split(";") if existing else []

        for f in request.files.getlist("Photo"):
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                name = f"{id}_{uuid.uuid4().hex}_{filename}"
                f.save(os.path.join(UPLOAD_DIR, name))
                photos.append(name)

        df.at[idx, "Photo"] = ";".join(photos)

        write_excel_atomic(INCIDENT_FILE, df)

        flash("Incident updated.", "success")
        return redirect(url_for("safety.incident_view", id=id))

    return render_template("safety/incident_form.html",
                           action="Edit",
                           data=df.loc[idx].to_dict())


@safety_bp.route("/incidents/<id>/delete")
def incident_delete(id):
    df = read_excel(INCIDENT_FILE)

    if id not in df["ID"].values:
        abort(404)

    row = df[df["ID"] == id].iloc[0]
    photos = row.Photo.split(";") if row.Photo else []

    for p in photos:
        full = os.path.join(UPLOAD_DIR, p)
        if os.path.exists(full):
            os.remove(full)

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
    return render_template("safety/corrective_list.html",
                           corrective=df.to_dict(orient="records"))


@safety_bp.route("/corrective/new", methods=["GET", "POST"])
def corrective_add():
    incident_param = request.args.get("incident", "")

    if request.method == "POST":
        rec = {
            "ID": make_id(),
            "Incident_ID": request.form.get("Incident_ID", incident_param),
            "Action": request.form.get("Action", ""),
            "Status": request.form.get("Status", "Open"),
            "Assigned_To": request.form.get("Assigned_To", ""),
            "Notes": request.form.get("Notes", ""),
            "Created_At": datetime.utcnow().isoformat(),
            "Updated_At": datetime.utcnow().isoformat()
        }

        df = read_excel(CORRECTIVE_FILE)
        write_excel_atomic(
            CORRECTIVE_FILE,
            pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        )

        flash("Corrective action saved.", "success")
        return redirect(url_for("safety.corrective_list"))

    # GET method
    return render_template(
        "safety/corrective_form.html",
        action="Add",
        data={"Incident_ID": incident_param}
    )


@safety_bp.route("/corrective/<id>/edit", methods=["GET", "POST"])
def corrective_edit(id):
    df = read_excel(CORRECTIVE_FILE)
    idx_list = df.index[df["ID"] == id].tolist()

    if not idx_list:
        abort(404)

    idx = idx_list[0]

    if request.method == "POST":
        df.at[idx, "Action"] = request.form.get("Action", df.at[idx, "Action"])
        df.at[idx, "Assigned_To"] = request.form.get("Assigned_To", df.at[idx, "Assigned_To"])
        df.at[idx, "Status"] = request.form.get("Status", df.at[idx, "Status"])
        df.at[idx, "Notes"] = request.form.get("Notes", df.at[idx, "Notes"])
        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()

        write_excel_atomic(CORRECTIVE_FILE, df)
        flash("Corrective action updated.", "success")
        return redirect(url_for("safety.corrective_list"))

    return render_template(
        "safety/corrective_form.html",
        action="Edit",
        data=df.loc[idx].to_dict()
    )

@safety_bp.route("/corrective/<id>")
def corrective_view(id):
    df = read_excel(CORRECTIVE_FILE)
    row = df[df["ID"] == id]

    if row.empty:
        abort(404)

    return render_template("safety/corrective_view.html",
                           rec=row.iloc[0].to_dict())


# ---------------------
# TRAINING
# ---------------------
@safety_bp.route("/training")
def training_list():
    df = read_excel(TRAINING_FILE)
    return render_template("safety/training_records.html",
                           training=df.to_dict(orient="records"))


@safety_bp.route("/training/new", methods=["GET", "POST"])
def training_add():
    if request.method == "POST":
        rec = {
            "ID": make_id(),
            "Date": request.form.get("Date", datetime.utcnow().date().isoformat()),
            "Employee": request.form.get("Employee", ""),
            "Topic": request.form.get("Topic", ""),
            "Trainer": request.form.get("Trainer", ""),
            "Expiry": request.form.get("Expiry", ""),
            "Notes": request.form.get("Notes", ""),
            "Created_At": datetime.utcnow().isoformat()
        }

        df = read_excel(TRAINING_FILE)
        write_excel_atomic(TRAINING_FILE,
                           pd.concat([df, pd.DataFrame([rec])], ignore_index=True))

        flash("Training record saved.", "success")
        return redirect(url_for("safety.training_list"))

    return render_template("safety/training_form.html",
                           action="Add", data={})

@safety_bp.route("/training/<id>")
def training_view(id):
    df = read_excel(TRAINING_FILE)
    row = df[df["ID"] == id]

    if row.empty:
        abort(404)

    return render_template("safety/training_view.html",
                           rec=row.iloc[0].to_dict())

@safety_bp.route("/training/<id>/edit", methods=["GET", "POST"])
def training_edit(id):
    df = read_excel(TRAINING_FILE)
    idx_list = df.index[df["ID"] == id].tolist()

    if not idx_list:
        abort(404)

    idx = idx_list[0]

    if request.method == "POST":
        df.at[idx, "Date"] = request.form.get("Date")
        df.at[idx, "Employee"] = request.form.get("Employee")
        df.at[idx, "Topic"] = request.form.get("Topic")
        df.at[idx, "Trainer"] = request.form.get("Trainer")
        df.at[idx, "Expiry"] = request.form.get("Expiry")
        df.at[idx, "Notes"] = request.form.get("Notes")

        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()

        write_excel_atomic(TRAINING_FILE, df)

        flash("Training record updated.", "success")
        return redirect(url_for("safety.training_view", id=id))

    return render_template(
        "safety/training_form.html",
        action="Edit",
        data=df.loc[idx].to_dict()
    )

# ---------------------
# TOOLBOX TALKS
# ---------------------
@safety_bp.route("/toolbox")
def toolbox_list():
    df = read_excel(TOOLBOX_FILE)
    return render_template("safety/toolbox_list.html",
                           talks=df.to_dict(orient="records"))


@safety_bp.route("/toolbox/new", methods=["GET", "POST"])
def toolbox_add():
    if request.method == "POST":
        rec = {
            "ID": make_id(),
            "Date": request.form.get("Date", datetime.utcnow().date().isoformat()),
            "Topic": request.form.get("Topic", ""),
            "Trainer": request.form.get("Trainer", ""),
            "Participants": request.form.get("Participants", ""),
            "Notes": request.form.get("Notes", ""),
            "Created_At": datetime.utcnow().isoformat()
        }

        df = read_excel(TOOLBOX_FILE)
        write_excel_atomic(TOOLBOX_FILE,
                           pd.concat([df, pd.DataFrame([rec])], ignore_index=True))

        flash("Toolbox Talk saved.", "success")
        return redirect(url_for("safety.toolbox_list"))

    return render_template("safety/toolbox_form.html",
                           action="Add", data={})


@safety_bp.route("/toolbox/<id>")
def toolbox_view(id):
    df = read_excel(TOOLBOX_FILE)
    row = df[df["ID"] == id]

    if row.empty:
        abort(404)

    return render_template("safety/toolbox_view.html",
                           rec=row.iloc[0].to_dict())


@safety_bp.route("/toolbox/<id>/edit", methods=["GET", "POST"])
def toolbox_edit(id):
    df = read_excel(TOOLBOX_FILE)
    idx_list = df.index[df["ID"] == id].tolist()

    if not idx_list:
        abort(404)

    idx = idx_list[0]

    if request.method == "POST":
        df.at[idx, "Date"] = request.form.get("Date")
        df.at[idx, "Topic"] = request.form.get("Topic")
        df.at[idx, "Trainer"] = request.form.get("Trainer")
        df.at[idx, "Participants"] = request.form.get("Participants")
        df.at[idx, "Notes"] = request.form.get("Notes")

        write_excel_atomic(TOOLBOX_FILE, df)

        flash("Toolbox Talk updated.", "success")
        return redirect(url_for("safety.toolbox_list"))

    return render_template("safety/toolbox_form.html",
                           action="Edit",
                           data=df.loc[idx].to_dict())


# ---------------------
# CHECKLISTS
# ---------------------
@safety_bp.route("/checklists")
def checklist_list():
    df = read_excel(CHECKLIST_FILE)
    return render_template("safety/checklists.html",
                           checklists=df.to_dict(orient="records"))


@safety_bp.route("/checklists/new", methods=["GET", "POST"])
def checklist_add():
    if request.method == "POST":
        rec = {
            "ID": make_id(),
            "Date": request.form.get("Date", datetime.utcnow().date().isoformat()),
            "Checklist_Name": request.form.get("Checklist_Name", ""),
            "Performed_By": request.form.get("Performed_By", ""),
            "Notes": request.form.get("Notes", ""),
            "Created_At": datetime.utcnow().isoformat()
        }

        df = read_excel(CHECKLIST_FILE)
        write_excel_atomic(CHECKLIST_FILE,
                           pd.concat([df, pd.DataFrame([rec])], ignore_index=True))

        flash("Checklist saved.", "success")
        return redirect(url_for("safety.checklist_list"))

    return render_template("safety/checklist_form.html",
                           action="Add", data={})

@safety_bp.route("/checklists/<id>")
def checklist_view(id):
    df = read_excel(CHECKLIST_FILE)
    row = df[df["ID"] == id]

    if row.empty:
        abort(404)

    return render_template(
        "safety/checklist_view.html",
        rec=row.iloc[0].to_dict()
    )

@safety_bp.route("/checklists/<id>/edit", methods=["GET", "POST"])
def checklist_edit(id):
    df = read_excel(CHECKLIST_FILE)
    idx_list = df.index[df["ID"] == id].tolist()

    if not idx_list:
        abort(404)

    idx = idx_list[0]

    if request.method == "POST":
        df.at[idx, "Date"] = request.form.get("Date")
        df.at[idx, "Checklist_Name"] = request.form.get("Checklist_Name")
        df.at[idx, "Performed_By"] = request.form.get("Performed_By")
        df.at[idx, "Notes"] = request.form.get("Notes")
        df.at[idx, "Updated_At"] = datetime.utcnow().isoformat()

        write_excel_atomic(CHECKLIST_FILE, df)

        flash("Checklist updated.", "success")
        return redirect(url_for("safety.checklist_view", id=id))

    return render_template(
        "safety/checklist_form.html",
        action="Edit",
        data=df.loc[idx].to_dict()
    )

# ---------------------
# EXPORT INCIDENTS
# ---------------------
@safety_bp.route("/incidents/export")
def incidents_export():
    df = read_excel(INCIDENT_FILE)
    out = os.path.join(
        DATA_DIR,
        f"safety_incidents_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    )
    df.to_excel(out, index=False)
    return send_file(out, as_attachment=True)

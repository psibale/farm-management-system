"""Main-system action tracking for mobile crop inspections."""

from datetime import date, datetime
from pathlib import Path
from threading import RLock

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from config import DATA_FOLDER
from modules.season import get_active_season


followups_bp = Blueprint("crop_followups", __name__)
INSPECTIONS_FILE = Path(DATA_FOLDER) / "crop_inspections.xlsx"
IRRIGATION_INSPECTIONS_FILE = Path(DATA_FOLDER) / "irrigation_inspections.xlsx"
PEST_DISEASE_INSPECTIONS_FILE = Path(DATA_FOLDER) / "mobile_pest_disease_inspections.xlsx"
FOLLOWUPS_FILE = Path(DATA_FOLDER) / "crop_inspection_followups.xlsx"
FOLLOWUP_COLUMNS = [
    "Inspection ID",
    "Inspection Type",
    "Status",
    "Assigned To",
    "Due Date",
    "Follow-up Notes",
    "Updated By",
    "Updated At",
    "Completed At",
]
WRITE_LOCK = RLock()
ALLOWED_STATUSES = {"Open", "In Progress", "Completed"}


def _clean(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _read(path):
    try:
        return pd.read_excel(path) if path.exists() else pd.DataFrame()
    except Exception as exc:
        raise RuntimeError(f"Could not read {path.name}: {exc}") from exc


def _followup_map():
    df = _read(FOLLOWUPS_FILE)
    result = {}
    if df.empty or "Inspection ID" not in df.columns:
        return result
    for _, row in df.iterrows():
        inspection_id = _clean(row.get("Inspection ID", ""))
        if inspection_id:
            result[inspection_id] = {
                "status": _clean(row.get("Status", "")) or "Open",
                "assigned_to": _clean(row.get("Assigned To", "")),
                "due_date": _clean(row.get("Due Date", ""))[:10],
                "notes": _clean(row.get("Follow-up Notes", "")),
                "updated_at": _clean(row.get("Updated At", "")),
                "completed_at": _clean(row.get("Completed At", "")),
            }
    return result


def _action_items(season_filter):
    sources = []
    for label, path in (
        ("Crop", INSPECTIONS_FILE),
        ("Irrigation", IRRIGATION_INSPECTIONS_FILE),
        ("Pest & Disease", PEST_DISEASE_INSPECTIONS_FILE),
    ):
        frame = _read(path)
        if not frame.empty and "Inspection ID" in frame.columns:
            sources.append((label, frame))

    followups = _followup_map()
    if not sources:
        return [], followups, []

    seasons = set()
    for _, frame in sources:
        if "Season" in frame.columns:
            seasons.update(
                _clean(value) for value in frame["Season"].dropna() if _clean(value)
            )
    seasons = sorted(seasons, reverse=True)

    today = date.today().isoformat()
    items = []
    for inspection_type, inspections in sources:
        if season_filter != "all" and "Season" in inspections.columns:
            inspections = inspections[
                inspections["Season"].fillna("").astype(str).str.strip() == season_filter
            ]
        for _, row in inspections.iterrows():
            inspection_id = _clean(row.get("Inspection ID", ""))
            if not inspection_id:
                continue
            priority = _clean(row.get("Priority", "Routine")) or "Routine"
            action = _clean(row.get("Recommended Action", ""))
            if priority not in {"Follow-up", "Urgent"} and not action:
                continue
            tracked = followups.get(inspection_id, {})
            status = tracked.get("status", "Open")
            due_date = tracked.get("due_date", "")
            overdue = bool(due_date and due_date < today and status != "Completed")
            inspection_date = row.get("Inspection Date", "")
            if hasattr(inspection_date, "strftime"):
                inspection_date = inspection_date.strftime("%Y-%m-%d")
            else:
                inspection_date = _clean(inspection_date)[:10]
            items.append({
                "inspection_id": inspection_id,
                "inspection_type": inspection_type,
                "inspection_date": inspection_date,
                "field": _clean(row.get("Field", "")),
                "main_field": _clean(row.get("Main Field", "")),
                "crop": _clean(row.get("Crop/Variety", "")),
                "stage": _clean(row.get("Growth Stage", "")) or _clean(row.get("Inspection Type", "")),
                "issue": _clean(row.get("Pest / Issue", "")),
                "finding_type": _clean(row.get("Pest/Disease Type", "")),
                "smut": _clean(row.get("SMUT%", "")),
                "ysa": _clean(row.get("YSA%", "")),
                "black_beetles": _clean(row.get("Black Beetles (ha)", "")),
                "lady_beetles": _clean(row.get("Lady Beetle", "")),
                "treatment": _clean(row.get("Pesticide Used", "")),
                "treated_area": _clean(row.get("Hectares", "")),
                "liters": _clean(row.get("Liters", "")),
                "priority": priority,
                "observations": _clean(row.get("Observations", "")),
                "action": action,
                "status": status,
                "assigned_to": tracked.get("assigned_to", ""),
                "due_date": due_date,
                "notes": tracked.get("notes", ""),
                "updated_at": tracked.get("updated_at", ""),
                "overdue": overdue,
            })
    items.sort(key=lambda item: (
        item["status"] == "Completed",
        not item["overdue"],
        item["priority"] != "Urgent",
        item["due_date"] or "9999-12-31",
        item["inspection_date"],
    ))
    return items, followups, seasons


@followups_bp.route("/crop-inspection-followups", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        inspection_id = request.form.get("inspection_id", "").strip()
        status = request.form.get("status", "Open").strip()
        assigned_to = request.form.get("assigned_to", "").strip()[:120]
        due_date = request.form.get("due_date", "").strip()
        notes = request.form.get("notes", "").strip()
        season_filter = request.form.get("season_filter", "all") or "all"
        if status not in ALLOWED_STATUSES:
            flash("Choose a valid follow-up status.", "danger")
            return redirect(url_for("crop_followups.index", season=season_filter))
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                flash("Enter a valid due date.", "danger")
                return redirect(url_for("crop_followups.index", season=season_filter))
        if len(notes) > 2000:
            flash("Follow-up notes must be 2,000 characters or fewer.", "danger")
            return redirect(url_for("crop_followups.index", season=season_filter))

        with WRITE_LOCK:
            valid_ids = set()
            for source_path in (INSPECTIONS_FILE, IRRIGATION_INSPECTIONS_FILE, PEST_DISEASE_INSPECTIONS_FILE):
                inspections = _read(source_path)
                if not inspections.empty and "Inspection ID" in inspections.columns:
                    valid_ids.update(
                        inspections["Inspection ID"].fillna("").astype(str).str.strip()
                    )
            if not valid_ids:
                flash("No mobile inspection records are available yet.", "warning")
                return redirect(url_for("crop_followups.index", season=season_filter))
            if inspection_id not in valid_ids:
                flash("That inspection record could not be found.", "danger")
                return redirect(url_for("crop_followups.index", season=season_filter))

            df = _read(FOLLOWUPS_FILE)
            for column in FOLLOWUP_COLUMNS:
                if column not in df.columns:
                    df[column] = ""
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            completed_at = now if status == "Completed" else ""
            values = {
                "Inspection ID": inspection_id,
                "Inspection Type": next((label for label, path in (("Crop", INSPECTIONS_FILE), ("Irrigation", IRRIGATION_INSPECTIONS_FILE), ("Pest & Disease", PEST_DISEASE_INSPECTIONS_FILE)) if inspection_id in set(_read(path).get("Inspection ID", pd.Series(dtype=str)).fillna("").astype(str).str.strip())), "Crop"),
                "Status": status,
                "Assigned To": assigned_to,
                "Due Date": due_date,
                "Follow-up Notes": notes,
                "Updated By": session.get("username", ""),
                "Updated At": now,
                "Completed At": completed_at,
            }
            if "Inspection ID" in df.columns and not df.empty:
                mask = df["Inspection ID"].fillna("").astype(str).str.strip() == inspection_id
            else:
                mask = pd.Series(False, index=df.index)
            if mask.any():
                for column, value in values.items():
                    df.loc[mask, column] = value
            else:
                df = pd.concat([df, pd.DataFrame([values])], ignore_index=True)
            df.to_excel(FOLLOWUPS_FILE, index=False)

        flash("Follow-up updated.", "success")
        return redirect(url_for("crop_followups.index", season=season_filter))

    active_season = str(get_active_season())
    season_filter = request.args.get("season", active_season).strip() or active_season
    try:
        items, _, seasons = _action_items(season_filter)
    except RuntimeError as exc:
        flash(str(exc), "danger")
        items, seasons = [], []

    season_items = list(items)
    selected_status = request.args.get("status", "All").strip()
    if selected_status == "Overdue":
        items = [item for item in items if item["overdue"]]
    elif selected_status in ALLOWED_STATUSES:
        items = [item for item in items if item["status"] == selected_status]
    else:
        selected_status = "All"

    counts = {
        "open": sum(item["status"] == "Open" for item in season_items),
        "in_progress": sum(item["status"] == "In Progress" for item in season_items),
        "overdue": sum(item["overdue"] for item in season_items),
        "urgent": sum(item["priority"] == "Urgent" and item["status"] != "Completed" for item in season_items),
    }
    return render_template(
        "crop_inspection_followups.html",
        items=items,
        counts=counts,
        seasons=seasons,
        season_filter=season_filter,
        selected_status=selected_status,
        active_season=active_season,
        today=date.today().isoformat(),
    )

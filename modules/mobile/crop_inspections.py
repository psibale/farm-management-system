"""Mobile crop inspection storage and field register helpers."""

from datetime import datetime
from pathlib import Path
from threading import RLock

import pandas as pd
from modules.excel_cache import read_excel_cached


_INSPECTION_COLUMNS = [
    "Inspection ID",
    "Inspection Date",
    "Field",
    "Main Field",
    "Area (ha)",
    "Crop/Variety",
    "Growth Stage",
    "Crop Vigor",
    "Stand Condition",
    "Weed Pressure",
    "Moisture Status",
    "Pest/Disease Signs",
    "Observations",
    "Recommended Action",
    "Priority",
    "Season",
    "Surveyor",
    "Recorded At",
]
_WRITE_LOCK = RLock()


def _text(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


class CropInspectionManager:
    def __init__(self, data_folder):
        self.data_folder = Path(data_folder)
        self.path = self.data_folder / "crop_inspections.xlsx"
        self.fields_path = self.data_folder / "registered_fields.xlsx"

    def registered_fields(self, season):
        if not self.fields_path.exists():
            return []
        try:
            df = read_excel_cached(self.fields_path)
        except Exception:
            return []
        if df.empty or "Field" not in df.columns:
            return []
        if "Season" in df.columns:
            selected = df[df["Season"].fillna("").astype(str).str.strip() == str(season)]
            if not selected.empty:
                df = selected
        result = []
        seen = set()
        for _, row in df.iterrows():
            field = _text(row.get("Field", ""))
            if not field or field in seen:
                continue
            seen.add(field)
            area = pd.to_numeric(row.get("Hectares", 0), errors="coerce")
            result.append({
                "field": field,
                "main_field": _text(row.get("Main Field", "")),
                "crop": _text(row.get("Crop Name", "")),
                "area": "" if pd.isna(area) else round(float(area), 3),
            })
        return sorted(result, key=lambda item: item["field"])

    def recent(self, season, limit=10):
        if not self.path.exists():
            return []
        try:
            df = read_excel_cached(self.path)
        except Exception:
            return []
        if df.empty:
            return []
        if "Season" in df.columns:
            df = df[df["Season"].fillna("").astype(str) == str(season)]
        if df.empty:
            return []
        df = df.tail(limit).iloc[::-1]
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": _text(row.get("Inspection Date", ""))[:10],
                "field": _text(row.get("Field", "")),
                "stage": _text(row.get("Growth Stage", "")),
                "vigor": _text(row.get("Crop Vigor", "")),
                "priority": _text(row.get("Priority", "")),
                "observations": _text(row.get("Observations", "")),
            })
        return result

    def save(self, data, surveyor, default_season):
        inspection_id = str(data.get("survey_id", "")).strip()
        field = str(data.get("field", "")).strip()
        inspection_date = str(data.get("inspection_date", "")).strip()
        if not inspection_id:
            raise ValueError("Inspection ID is missing; save the inspection again.")
        if not field:
            raise ValueError("Select a field before saving.")
        try:
            datetime.strptime(inspection_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Enter a valid inspection date.") from exc

        choices = {
            "growth_stage": {"Establishment", "Tillering", "Grand growth", "Maturation", "Ratoon regrowth", "Other"},
            "crop_vigor": {"Good", "Fair", "Poor", "Not assessed"},
            "stand_condition": {"Good", "Fair", "Poor", "Not assessed"},
            "weed_pressure": {"None", "Low", "Moderate", "High", "Not assessed"},
            "moisture_status": {"Dry", "Adequate", "Waterlogged", "Not assessed"},
            "priority": {"Routine", "Follow-up", "Urgent"},
        }
        values = {}
        for key, allowed in choices.items():
            value = str(data.get(key, "")).strip()
            if value not in allowed:
                raise ValueError("Choose a valid value for " + key.replace("_", " ") + ".")
            values[key] = value

        observations = str(data.get("observations", "")).strip()
        if not observations:
            raise ValueError("Describe what you observed before saving.")
        if len(observations) > 3000:
            raise ValueError("Observations must be 3,000 characters or fewer.")

        row = {
            "Inspection ID": inspection_id,
            "Inspection Date": inspection_date,
            "Field": field,
            "Main Field": str(data.get("main_field", "")).strip(),
            "Area (ha)": data.get("area_ha", ""),
            "Crop/Variety": str(data.get("crop_variety", "")).strip(),
            "Growth Stage": values["growth_stage"],
            "Crop Vigor": values["crop_vigor"],
            "Stand Condition": values["stand_condition"],
            "Weed Pressure": values["weed_pressure"],
            "Moisture Status": values["moisture_status"],
            "Pest/Disease Signs": str(data.get("pest_disease_signs", "")).strip()[:1000],
            "Observations": observations,
            "Recommended Action": str(data.get("recommended_action", "")).strip()[:2000],
            "Priority": values["priority"],
            "Season": str(data.get("season") or default_season),
            "Surveyor": surveyor,
            "Recorded At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.data_folder.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            df = read_excel_cached(self.path) if self.path.exists() else pd.DataFrame(columns=_INSPECTION_COLUMNS)
            if "Inspection ID" in df.columns:
                saved = df[df["Inspection ID"].fillna("").astype(str).str.strip() == inspection_id]
                if not saved.empty:
                    old = saved.iloc[-1]
                    return {"field": str(old.get("Field", field)), "duplicate": True}
            for column in _INSPECTION_COLUMNS:
                if column not in df.columns:
                    df[column] = ""
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_excel(self.path, index=False)
        return {"field": field, "duplicate": False}

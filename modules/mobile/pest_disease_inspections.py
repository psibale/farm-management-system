"""Mobile pest and disease inspection storage helpers."""

from datetime import datetime
from pathlib import Path
from threading import RLock
import math

import pandas as pd

from modules.mobile.crop_inspections import CropInspectionManager


_COLUMNS = [
    "Inspection ID", "Inspection Date", "Field", "Main Field", "Area (ha)",
    "Inspection Type", "Pest/Disease Type", "Crop/Variety", "SMUT%", "YSA%",
    "Black Beetles (ha)", "Lady Beetle", "Pest / Issue", "Hectares",
    "Pesticide Used", "Liters", "Mandays", "Observations",
    "Recommended Action", "Priority", "Season", "Surveyor", "Recorded At",
]
_WRITE_LOCK = RLock()


def _text(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _optional_number(data, key, label, maximum=None):
    raw = _text(data.get(key, ""))
    if not raw:
        return ""
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Enter a valid number for {label}.") from exc
    if not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum):
        limit = f" between 0 and {maximum}" if maximum is not None else " greater than or equal to 0"
        raise ValueError(f"{label} must be{limit}.")
    return value


class PestDiseaseInspectionManager:
    def __init__(self, data_folder):
        self.data_folder = Path(data_folder)
        self.path = self.data_folder / "mobile_pest_disease_inspections.xlsx"
        self.field_manager = CropInspectionManager(data_folder)

    def registered_fields(self, season):
        return self.field_manager.registered_fields(season)

    def recent(self, season, limit=10):
        if not self.path.exists():
            return []
        try:
            df = pd.read_excel(self.path)
        except Exception:
            return []
        if df.empty:
            return []
        if "Season" in df.columns:
            df = df[df["Season"].fillna("").astype(str) == str(season)]
        result = []
        for _, row in df.tail(limit).iloc[::-1].iterrows():
            value = row.get("Inspection Date", "")
            if hasattr(value, "strftime"):
                value = value.strftime("%Y-%m-%d")
            result.append({
                "date": _text(value)[:10],
                "field": _text(row.get("Field", "")),
                "type": _text(row.get("Inspection Type", "")),
                "priority": _text(row.get("Priority", "")),
                "issue": _text(row.get("Pest / Issue", "")),
                "observations": _text(row.get("Observations", "")),
            })
        return result

    def save(self, data, surveyor, default_season):
        inspection_id = _text(data.get("survey_id", ""))
        field = _text(data.get("field", ""))
        inspection_date = _text(data.get("inspection_date", ""))
        kind = _text(data.get("inspection_type", ""))
        pest_disease_type = _text(data.get("pest_disease_type", ""))
        if not inspection_id:
            raise ValueError("Inspection ID is missing; save the record again.")
        if not field:
            raise ValueError("Select a field before saving.")
        try:
            datetime.strptime(inspection_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Enter a valid inspection date.") from exc
        if kind not in {"Disease Inspection", "Pest Inspection", "Pest Control"}:
            raise ValueError("Choose Disease Inspection, Pest Inspection, or Pest Control.")
        if pest_disease_type not in {"Disease", "Pest", "Both", "Not sure"}:
            raise ValueError("Choose a valid pest or disease type.")

        priority = _text(data.get("priority", ""))
        if priority not in {"Routine", "Follow-up", "Urgent"}:
            raise ValueError("Choose a valid follow-up priority.")
        observations = _text(data.get("observations", ""))
        if not observations:
            raise ValueError("Describe the pest or disease finding before saving.")
        if len(observations) > 3000:
            raise ValueError("Observations must be 3,000 characters or fewer.")

        smut = _optional_number(data, "smut_percent", "SMUT percent", 100)
        ysa = _optional_number(data, "ysa_percent", "YSA percent", 100)
        beetles = _optional_number(data, "black_beetles_per_ha", "Black beetles per hectare")
        lady_beetles = _optional_number(data, "lady_beetle_count", "Lady beetle count")
        hectares = _optional_number(data, "hectares", "Hectares treated")
        liters = _optional_number(data, "liters", "Liters used")
        mandays = _optional_number(data, "mandays", "Mandays")
        pesticide = _text(data.get("pesticide_used", ""))
        if kind == "Pest Control":
            if not pesticide:
                raise ValueError("Enter the pesticide or control method used.")
            if hectares == "" or hectares <= 0:
                raise ValueError("Enter the hectares treated.")
        if kind == "Disease Inspection" and smut == "" and ysa == "" and not observations:
            raise ValueError("Enter a disease finding or describe what you observed.")

        row = {
            "Inspection ID": inspection_id,
            "Inspection Date": inspection_date,
            "Field": field,
            "Main Field": _text(data.get("main_field", "")),
            "Area (ha)": data.get("area_ha", ""),
            "Inspection Type": kind,
            "Pest/Disease Type": pest_disease_type,
            "Crop/Variety": _text(data.get("crop_variety", "")),
            "SMUT%": smut,
            "YSA%": ysa,
            "Black Beetles (ha)": beetles,
            "Lady Beetle": lady_beetles,
            "Pest / Issue": _text(data.get("issue_name", ""))[:240],
            "Hectares": hectares,
            "Pesticide Used": pesticide,
            "Liters": liters,
            "Mandays": mandays,
            "Observations": observations,
            "Recommended Action": _text(data.get("recommended_action", ""))[:2000],
            "Priority": priority,
            "Season": _text(data.get("season")) or str(default_season),
            "Surveyor": surveyor,
            "Recorded At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data_folder.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            df = pd.read_excel(self.path) if self.path.exists() else pd.DataFrame(columns=_COLUMNS)
            if "Inspection ID" in df.columns:
                saved = df[df["Inspection ID"].fillna("").astype(str).str.strip() == inspection_id]
                if not saved.empty:
                    return {"field": _text(saved.iloc[-1].get("Field", field)), "duplicate": True}
            for column in _COLUMNS:
                if column not in df.columns:
                    df[column] = ""
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_excel(self.path, index=False)
        return {"field": field, "duplicate": False}

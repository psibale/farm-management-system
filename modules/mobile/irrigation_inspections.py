"""Mobile irrigation inspection storage helpers."""

from datetime import datetime
from pathlib import Path
from threading import RLock

import pandas as pd

from modules.mobile.crop_inspections import CropInspectionManager


_IRRIGATION_COLUMNS = [
    "Inspection ID", "Inspection Date", "Field", "Main Field", "Area (ha)",
    "Irrigation Method", "Water Source", "Soil Moisture", "System Condition",
    "Water Distribution", "Observed Issues", "Observations", "Recommended Action",
    "Priority", "Season", "Surveyor", "Recorded At",
]
_WRITE_LOCK = RLock()


def _text(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


class IrrigationInspectionManager:
    def __init__(self, data_folder):
        self.data_folder = Path(data_folder)
        self.path = self.data_folder / "irrigation_inspections.xlsx"
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
                "system": _text(row.get("System Condition", "")),
                "priority": _text(row.get("Priority", "")),
                "observations": _text(row.get("Observations", "")),
            })
        return result

    def save(self, data, surveyor, default_season):
        inspection_id = _text(data.get("survey_id", ""))
        field = _text(data.get("field", ""))
        inspection_date = _text(data.get("inspection_date", ""))
        if not inspection_id:
            raise ValueError("Inspection ID is missing; save the inspection again.")
        if not field:
            raise ValueError("Select a field before saving.")
        try:
            datetime.strptime(inspection_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Enter a valid inspection date.") from exc

        choices = {
            "irrigation_method": {"Furrow", "Centre pivot", "Sprinkler", "Drip", "Other", "Not assessed"},
            "water_source": {"Canal", "Borehole", "Dam / reservoir", "River", "Other", "Not assessed"},
            "soil_moisture": {"Dry", "Adequate", "Wet / waterlogged", "Not assessed"},
            "system_condition": {"Working well", "Needs maintenance", "Not functioning", "Not assessed"},
            "water_distribution": {"Even", "Uneven", "Poor / no water", "Not assessed"},
            "priority": {"Routine", "Follow-up", "Urgent"},
        }
        values = {}
        for key, allowed in choices.items():
            value = _text(data.get(key, ""))
            if value not in allowed:
                raise ValueError("Choose a valid value for " + key.replace("_", " ") + ".")
            values[key] = value

        observations = _text(data.get("observations", ""))
        if not observations:
            raise ValueError("Describe the irrigation condition you observed.")
        if len(observations) > 3000:
            raise ValueError("Observations must be 3,000 characters or fewer.")

        row = {
            "Inspection ID": inspection_id,
            "Inspection Date": inspection_date,
            "Field": field,
            "Main Field": _text(data.get("main_field", "")),
            "Area (ha)": data.get("area_ha", ""),
            "Irrigation Method": values["irrigation_method"],
            "Water Source": values["water_source"],
            "Soil Moisture": values["soil_moisture"],
            "System Condition": values["system_condition"],
            "Water Distribution": values["water_distribution"],
            "Observed Issues": _text(data.get("observed_issues", ""))[:1500],
            "Observations": observations,
            "Recommended Action": _text(data.get("recommended_action", ""))[:2000],
            "Priority": values["priority"],
            "Season": _text(data.get("season")) or str(default_season),
            "Surveyor": surveyor,
            "Recorded At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data_folder.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            df = pd.read_excel(self.path) if self.path.exists() else pd.DataFrame(columns=_IRRIGATION_COLUMNS)
            if "Inspection ID" in df.columns:
                saved = df[df["Inspection ID"].fillna("").astype(str).str.strip() == inspection_id]
                if not saved.empty:
                    return {"field": _text(saved.iloc[-1].get("Field", field)), "duplicate": True}
            for column in _IRRIGATION_COLUMNS:
                if column not in df.columns:
                    df[column] = ""
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_excel(self.path, index=False)
        return {"field": field, "duplicate": False}

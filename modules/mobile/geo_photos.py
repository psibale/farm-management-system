"""Offline-synced mobile geo-tagged photo storage."""

from base64 import b64decode
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

import pandas as pd


_COLUMNS = [
    "Photo ID", "Inspection Date", "Field", "Main Field", "Latitude",
    "Longitude", "GPS Accuracy (m)", "Category", "Notes", "Photo File",
    "Season", "Surveyor", "Recorded At",
]
_WRITE_LOCK = RLock()
_MAX_PHOTO_BYTES = 900_000


def _text(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


class GeoPhotoManager:
    def __init__(self, data_folder, static_folder):
        self.data_folder = Path(data_folder)
        self.workbook = self.data_folder / "mobile_geo_photos.xlsx"
        self.photo_folder = Path(static_folder) / "mobile_geo_photos"

    def recent(self, season, limit=20):
        if not self.workbook.exists():
            return []
        try:
            frame = pd.read_excel(self.workbook)
        except Exception:
            return []
        if frame.empty:
            return []
        if "Season" in frame.columns:
            frame = frame[frame["Season"].fillna("").astype(str) == str(season)]
        items = []
        for _, row in frame.tail(limit).iloc[::-1].iterrows():
            when = row.get("Inspection Date", "")
            if hasattr(when, "strftime"):
                when = when.strftime("%Y-%m-%d")
            items.append({
                "date": _text(when)[:10],
                "field": _text(row.get("Field", "")),
                "category": _text(row.get("Category", "")),
                "notes": _text(row.get("Notes", "")),
                "photo": _text(row.get("Photo File", "")),
                "latitude": _text(row.get("Latitude", "")),
                "longitude": _text(row.get("Longitude", "")),
            })
        return items

    def save(self, data, surveyor, default_season):
        photo_id = _text(data.get("survey_id", ""))
        field = _text(data.get("field", ""))
        photo_date = _text(data.get("photo_date", ""))
        if not photo_id or len(photo_id) > 120:
            raise ValueError("Photo record ID is missing or invalid.")
        if not field or len(field) > 120:
            raise ValueError("Select or enter a valid field.")
        try:
            datetime.strptime(photo_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Enter a valid photo date.") from exc
        try:
            latitude = float(data.get("latitude"))
            longitude = float(data.get("longitude"))
            accuracy = float(data.get("gps_accuracy"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Capture a GPS location before saving the photo.") from exc
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("The captured GPS coordinates are invalid.")
        if not (0 <= accuracy <= 1000):
            raise ValueError("GPS accuracy must be between 0 and 1,000 metres.")
        category = _text(data.get("category", ""))
        if category not in {"Crop condition", "Pest or disease", "Irrigation", "Damage", "Other"}:
            raise ValueError("Choose a valid photo category.")
        notes = _text(data.get("notes", ""))
        if len(notes) > 1500:
            raise ValueError("Photo notes must be 1,500 characters or fewer.")
        photo_data = _text(data.get("photo_data", ""))
        prefix = "data:image/jpeg;base64,"
        if not photo_data.startswith(prefix):
            raise ValueError("Choose a photo captured or saved as JPEG.")
        try:
            image_bytes = b64decode(photo_data[len(prefix):], validate=True)
        except Exception as exc:
            raise ValueError("The photo data could not be read. Please choose it again.") from exc
        if not image_bytes or len(image_bytes) > _MAX_PHOTO_BYTES:
            raise ValueError("The compressed photo must be smaller than 900 KB. Retake it or choose a smaller image.")
        if not image_bytes.startswith(b"\xff\xd8\xff"):
            raise ValueError("The uploaded image is not a valid JPEG photo.")

        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.photo_folder.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            frame = pd.read_excel(self.workbook) if self.workbook.exists() else pd.DataFrame(columns=_COLUMNS)
            if "Photo ID" in frame.columns:
                saved = frame[frame["Photo ID"].fillna("").astype(str).str.strip() == photo_id]
                if not saved.empty:
                    return {"field": _text(saved.iloc[-1].get("Field", field)), "duplicate": True}
            for column in _COLUMNS:
                if column not in frame.columns:
                    frame[column] = ""
            filename = f"{uuid4().hex}.jpg"
            path = self.photo_folder / filename
            path.write_bytes(image_bytes)
            row = {
                "Photo ID": photo_id,
                "Inspection Date": photo_date,
                "Field": field,
                "Main Field": _text(data.get("main_field", "")),
                "Latitude": latitude,
                "Longitude": longitude,
                "GPS Accuracy (m)": round(accuracy, 1),
                "Category": category,
                "Notes": notes,
                "Photo File": filename,
                "Season": _text(data.get("season")) or str(default_season),
                "Surveyor": surveyor,
                "Recorded At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            try:
                frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
                frame.to_excel(self.workbook, index=False)
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return {"field": field, "duplicate": False}

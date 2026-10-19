"""
=========================================================
DCGL FIELDMATE
Survey Manager
Version 2.1
=========================================================

Handles all mobile survey business logic.

Responsibilities

    • Main Fields
    • Sub-fields
    • Survey Validation
    • Automatic Sub-field Naming
    • Parent Field Statistics
    • Remaining Area Calculations

Future

    • SQL Database
    • Offline Sync
    • AI Survey Assistant
    • Android APK

=========================================================
"""

from pathlib import Path
import pandas as pd
from datetime import datetime
from threading import RLock
import json


_SURVEY_WRITE_LOCK = RLock()


class SurveyManager:

    # --------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------

    def __init__(self, data_folder):

        self.data_folder = Path(data_folder)

        self.field_file = self.data_folder / "field_polygons.xlsx"

        self.subfield_file = self.data_folder / "sub_fields.xlsx"

        self.main_fields = pd.DataFrame()

        self.sub_fields = pd.DataFrame()

        self.load_data()

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    def load_data(self):

        try:

            if self.field_file.exists():
                self.main_fields = pd.read_excel(self.field_file)
            else:
                self.main_fields = pd.DataFrame()

        except Exception:

            self.main_fields = pd.DataFrame()

        try:

            if self.subfield_file.exists():
                self.sub_fields = pd.read_excel(self.subfield_file)
            else:
                self.sub_fields = pd.DataFrame()

        except Exception:

            self.sub_fields = pd.DataFrame()

    # --------------------------------------------------
    # REFRESH
    # --------------------------------------------------

    def refresh(self):

        self.load_data()

    # --------------------------------------------------
    # SURVEY ID DUPLICATE PROTECTION
    # --------------------------------------------------

    def survey_exists_by_id(self, survey_id):

        if not survey_id:
            return False

        survey_id = str(survey_id).strip()

        # ----------------------------------------------
        # CHECK MAIN FIELDS
        # ----------------------------------------------

        if (
            not self.main_fields.empty
            and "Survey ID" in self.main_fields.columns
        ):

            existing = (
                self.main_fields["Survey ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            if survey_id in existing.values:
                return True

        # ----------------------------------------------
        # CHECK SUB-FIELDS
        # ----------------------------------------------

        if (
            not self.sub_fields.empty
            and "Survey ID" in self.sub_fields.columns
        ):

            existing = (
                self.sub_fields["Survey ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            if survey_id in existing.values:
                return True

        return False
    # --------------------------------------------------
    # SYSTEM INFO
    # --------------------------------------------------

    def system_info(self):

        return {

            "system": "DCGL FieldMate",

            "version": "2.1"

        }

    # --------------------------------------------------
    # MAIN FIELDS
    # --------------------------------------------------

    def get_parent_fields(self):

        if self.main_fields.empty:

            return []

        if "Field" not in self.main_fields.columns:

            return []

        return sorted(

            self.main_fields["Field"]

            .dropna()

            .astype(str)

            .str.strip()

            .unique()

            .tolist()

        )

    # --------------------------------------------------
    # SUBFIELDS
    # --------------------------------------------------

    def get_subfields(self, parent):

        if self.sub_fields.empty:

            return []

        if "Parent Field" not in self.sub_fields.columns:

            return []

        df = self.sub_fields[

            self.sub_fields["Parent Field"]

            .astype(str)

            .str.strip()

            == parent

        ]

        if df.empty:

            return []

        return sorted(

            df["Sub-field"]

            .dropna()

            .astype(str)

            .str.strip()

            .tolist()

        )

    # --------------------------------------------------
    # TOTALS
    # --------------------------------------------------

    def total_fields(self):

        return len(self.get_parent_fields())

    def total_subfields(self):

        if self.sub_fields.empty:

            return 0

        return len(self.sub_fields.index)

    # --------------------------------------------------
    # EXISTS
    # --------------------------------------------------

    def field_exists(self, field):

        return field in self.get_parent_fields()

    def subfield_exists(self, parent, subfield):

        return subfield in self.get_subfields(parent)

    # --------------------------------------------------
    # PARENT INFORMATION
    # --------------------------------------------------

    def get_parent_info(self, parent):

        if self.main_fields.empty:

            return None

        if "Field" not in self.main_fields.columns:

            return None

        df = self.main_fields[

            self.main_fields["Field"]

            .astype(str)

            .str.strip()

            == parent

        ]

        if df.empty:

            return None

        row = df.iloc[0]

        return {

            "field": row.get("Field", ""),

            "crop": row.get("Crop", ""),

            "soil": row.get("Soil", ""),

            "area": float(row.get("Area (Ha)", 0))

        }

    # --------------------------------------------------
    # REMAINING AREA
    # --------------------------------------------------

    def remaining_area(self, parent):

        info = self.get_parent_info(parent)

        if info is None:

            return {

                "parent_area": 0,

                "surveyed_area": 0,

                "remaining_area": 0

            }

        parent_area = info["area"]

        surveyed = 0

        if not self.sub_fields.empty:

            df = self.sub_fields[

                self.sub_fields["Parent Field"]

                .astype(str)

                .str.strip()

                == parent

            ]

            if not df.empty:

                surveyed = df["Area (Ha)"].fillna(0).sum()

        remaining = max(parent_area - surveyed, 0)

        return {

            "parent_area": round(parent_area, 3),

            "surveyed_area": round(surveyed, 3),

            "remaining_area": round(remaining, 3)

        }

    # --------------------------------------------------
    # NEXT SUBFIELD NAME
    # --------------------------------------------------

    def generate_subfield_name(self, parent):

        existing = self.get_subfields(parent)

        if not existing:

            return parent[:-2] + "01"

        prefix = parent[:-2]
        numbers = []

        for field in existing:

            field = str(field).strip()

            if not field.startswith(prefix):
                continue

            suffix = field[len(prefix):]

            if suffix.isdigit():
                numbers.append(int(suffix))

        next_number = max(numbers, default=0) + 1

        return f"{prefix}{next_number:02d}"

    # --------------------------------------------------
    # SAVE MAIN FIELD
    # --------------------------------------------------

    def save_main_field(self, data):

        self.load_data()

        # ----------------------------------------------
        # SURVEY ID
        # ----------------------------------------------

        survey_id = str(
            data.get("survey_id", "")
        ).strip()

        if not survey_id:

            raise ValueError(
                "Survey ID is missing."
            )

        # ----------------------------------------------
        # DUPLICATE PROTECTION
        # ----------------------------------------------

        if self.survey_exists_by_id(survey_id):

            print(
                "=" * 60
            )

            print(
                "SURVEY ALREADY SAVED"
            )

            print(
                "Survey ID:",
                survey_id
            )

            print(
                "=" * 60
            )

            # Treat duplicate as successful.
            # This is important for offline synchronisation.
            return True

        # ----------------------------------------------
        # BUILD ROW
        # ----------------------------------------------

        row = {

            "Survey ID":
                survey_id,

            "Field":
                data["field"],

            "Crop":
                data.get("crop", ""),

            "Soil":
                data.get("soil", ""),

            "Area (Ha)":
                round(
                    float(
                        data.get("area", 0)
                    ),
                    3
                ),

            "GeoJSON":
                json.dumps(
                    data["geojson"]
                ),

            "Stress Level":
                "Low",

            "Survey Date":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),

            "Surveyor":
                data.get(
                    "surveyor",
                    ""
                )

        }

        # ----------------------------------------------
        # ADD ROW
        # ----------------------------------------------

        self.main_fields = pd.concat(

            [

                self.main_fields,

                pd.DataFrame([row])

            ],

            ignore_index=True

        )

        # ----------------------------------------------
        # SAVE EXCEL
        # ----------------------------------------------

        self.main_fields.to_excel(

            self.field_file,

            index=False

        )

        print(
            "Main field survey saved:",
            survey_id
        )

        return True

    # --------------------------------------------------
    # SAVE SUBFIELD
    # --------------------------------------------------

    def save_subfield(self, data):

        self.load_data()

        # ----------------------------------------------
        # SURVEY ID
        # ----------------------------------------------

        survey_id = str(
            data.get("survey_id", "")
        ).strip()

        if not survey_id:

            raise ValueError(
                "Survey ID is missing."
            )

        # ----------------------------------------------
        # DUPLICATE PROTECTION
        # ----------------------------------------------

        if self.survey_exists_by_id(survey_id):

            print(
                "=" * 60
            )

            print(
                "SUB-FIELD SURVEY ALREADY SAVED"
            )

            print(
                "Survey ID:",
                survey_id
            )

            print(
                "=" * 60
            )

            saved = self.sub_fields[
                self.sub_fields["Survey ID"].fillna("").astype(str).str.strip()
                == survey_id
            ]
            if not saved.empty and "Sub-field" in saved.columns:
                data["field"] = str(saved.iloc[-1]["Sub-field"]).strip()

            return True

        # ----------------------------------------------
        # RESOLVE OFFLINE NUMBER COLLISIONS
        # ----------------------------------------------

        # Multiple devices may independently choose the same next number
        # while disconnected. The survey ID remains the idempotency key;
        # assign the next free field number when this record reaches the
        # server so both surveys are retained in the existing workbook.
        parent = str(data["parent"]).strip()
        requested_field = str(data["field"]).strip()
        existing_fields = set(self.get_subfields(parent))
        field_name = requested_field

        if field_name in existing_fields:
            field_name = self.generate_subfield_name(parent)

        data["field"] = field_name

        # ----------------------------------------------
        # BUILD ROW
        # ----------------------------------------------

        row = {

            "Survey ID":
                survey_id,

            "Parent Field":
                parent,

            "Sub-field":
                field_name,

            "Area (Ha)":
                round(
                    float(
                        data.get("area", 0)
                    ),
                    3
                ),

            "GeoJSON":
                json.dumps(
                    data["geojson"]
                ),

            "Survey Date":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),

            "Surveyor":
                data.get(
                    "surveyor",
                    ""
                )

        }

        # ----------------------------------------------
        # ADD ROW
        # ----------------------------------------------

        self.sub_fields = pd.concat(

            [

                self.sub_fields,

                pd.DataFrame([row])

            ],

            ignore_index=True

        )

        # ----------------------------------------------
        # SAVE EXCEL
        # ----------------------------------------------

        self.sub_fields.to_excel(

            self.subfield_file,

            index=False

        )

        print(
            "Sub-field survey saved:",
            survey_id
        )

        return True

    # --------------------------------------------------
    # SAVE SURVEY
    # --------------------------------------------------

    def save_survey(self, data):

        # Reload and serialize workbook writes so concurrent device uploads
        # choose sub-field numbers from the latest saved rows.
        with _SURVEY_WRITE_LOCK:
            self.load_data()
            survey_type = data.get("survey_type")

            if survey_type == "Main Field":
                return self.save_main_field(data)

            if survey_type == "Sub-field":
                return self.save_subfield(data)

            raise ValueError(
                f"Unknown survey type: {survey_type}"
            )

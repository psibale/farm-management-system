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

        numbers = []

        for field in existing:

            try:

                numbers.append(int(field[-2:]))

            except ValueError:

                continue

        if not numbers:

            return parent[:-2] + "01"

        next_number = max(numbers) + 1

        return f"{parent[:-2]}{next_number:02d}"
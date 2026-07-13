"""
GIS Audit Service

Checks all farm fields
from field_polygons.xlsx
"""

from .field_service import FieldService
from .validator import GISValidator



class GISAudit:


    @classmethod
    def run_audit(cls):

        fields = FieldService.load_fields()


        results = []


        for _, row in fields.iterrows():

            field_name = row["Field"]


            points = FieldService.load_field_boundary(
                field_name
            )


            if not points:

                continue


            report = GISValidator.create_report(
                points
            )

            results.append({

                "field":
                    field_name,

                "registered_area":
                    row["Area (Ha)"],

                "gis_area":
                    round(
                        report.field_area_ha,
                        2
                    ),

                "quality":
                    report.quality_score,

                "status":
                    "OK"
                    if report.quality_score >= 100
                    else "Review Required",

                "valid":
                    report.valid,

                "errors":
                    report.errors,

                "warnings":
                    report.warnings

            })


        return results
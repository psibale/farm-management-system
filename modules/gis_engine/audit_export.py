"""
GIS Audit Excel Export

Creates farm GIS quality reports
"""

import os
import pandas as pd


class GISAuditExport:


    @staticmethod
    def export_excel(
        results,
        filename="data/gis_audit_report.xlsx"
    ):


        rows = []


        for field in results:


            warning_text = "; ".join(
                field["warnings"]
            )


            error_text = "; ".join(
                field["errors"]
            )


            rows.append({

                "Field":
                    field["field"],

                "Registered Area (Ha)":
                    field["registered_area"],

                "GIS Area (Ha)":
                    field["gis_area"],

                "Quality Score (%)":
                    field["quality"],

                "Valid":
                    field["valid"],

                "Errors":
                    error_text,

                "Warnings":
                    warning_text

            })


        df = pd.DataFrame(rows)


        os.makedirs(
            os.path.dirname(filename),
            exist_ok=True
        )


        df.to_excel(
            filename,
            index=False
        )


        return filename
    
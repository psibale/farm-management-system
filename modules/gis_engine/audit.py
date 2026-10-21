"""
GIS Audit Service

Checks all farm fields
from field_polygons.xlsx
"""

import copy
import os
import threading

from .field_service import FieldService
from .validator import GISValidator



class GISAudit:

    _cache_lock = threading.Lock()
    _cache_signature = None
    _cache_results = None


    @classmethod
    def run_audit(cls):

        try:
            stat = os.stat(FieldService.DATA_FILE)
            signature = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        except OSError:
            signature = None

        with cls._cache_lock:
            if cls._cache_signature == signature and cls._cache_results is not None:
                return copy.deepcopy(cls._cache_results)

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


        with cls._cache_lock:
            cls._cache_signature = signature
            cls._cache_results = copy.deepcopy(results)

        return results

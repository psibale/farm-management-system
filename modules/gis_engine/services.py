"""
services.py

Business logic layer for GIS operations.

Farm Management System GIS Engine
"""

from typing import List, Dict

from .calculations import Coordinate
from .validator import GISValidator
from .geojson_utils import GeoJSONUtils


class GISService:
    """
    Main service layer for field GIS operations.
    """


    @staticmethod
    def process_field_boundary(
        coordinates: List[Coordinate],
        field_data: Dict
    ) -> Dict:
        """
        Complete field boundary processing.

        Steps:

        1. Validate GPS points
        2. Create validation report
        3. Generate GeoJSON
        4. Return complete field package
        """


        # -------------------------
        # Validation
        # -------------------------

        report = GISValidator.create_report(
            coordinates
        )


        # Stop if invalid

        if not report.valid:

            return {

                "success": False,

                "report":
                    report.to_dict()

            }


        # -------------------------
        # GeoJSON Creation
        # -------------------------

        geojson = (
            GeoJSONUtils
            .create_field_feature(
                coordinates,
                field_data
            )
        )


        # -------------------------
        # Final Result
        # -------------------------

        return {


            "success": True,


            "field": {

                "name":
                    field_data.get(
                        "field_name"
                    ),

                "estate":
                    field_data.get(
                        "estate"
                    )

            },


            "report":
                report.to_dict(),


            "geojson":
                geojson

        }
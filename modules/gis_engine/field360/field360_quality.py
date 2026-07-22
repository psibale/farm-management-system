"""
Field360 GIS Quality
"""

from ..gis_quality import get_field_quality


def get_gis_quality(field_name):

    try:

        result = get_field_quality(field_name)

        if not result:

            return {

                "quality": 0,

                "status": "Unknown",

                "warnings": []

            }

        # ---------------------------------
        # Determine Status
        # ---------------------------------

        if result["quality"] >= 100:

            status = "Excellent"

        elif result["quality"] >= 90:

            status = "Review"

        else:

            status = "Invalid"

        return {

            "quality": result["quality"],

            "status": status,

            "warnings": result["warnings"]

        }

    except Exception as e:

        print("GIS Quality Error:", e)

        return {

            "quality": 0,

            "status": "Unknown",

            "warnings": []

        }
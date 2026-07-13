"""
field_service.py

Farm Management System field operations.

Connects GIS Engine with:
- field_polygons.xlsx
- registered_fields.xlsx
- Leaflet maps

"""

import os
import pandas as pd
import json

from .calculations import Coordinate
from .services import GISService


class FieldService:
    """
    Service layer for farm fields.
    """

    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    DATA_FILE = os.path.join(
        BASE_DIR,
        "data",
        "field_polygons.xlsx"
    )


    @classmethod
    def load_fields(cls):
        """
        Load existing field boundaries.
        """

        if not os.path.exists(cls.DATA_FILE):
            raise FileNotFoundError(
                f"GIS field file not found: {cls.DATA_FILE}"
            )


        return pd.read_excel(
            cls.DATA_FILE
        )


    @classmethod
    def get_field(cls, field_name):
        """
        Retrieve a single field.
        """

        df = cls.load_fields()


        result = df[
            df["Field"] == field_name
        ]


        if result.empty:

            return None


        return result.iloc[0].to_dict()


    @classmethod
    def validate_field(
        cls,
        coordinates
    ):
        """
        Validate an existing field boundary.
        """

        return GISService.process_field_boundary(
            coordinates,
            {}
        )

    @classmethod
    def load_field_boundary(
        cls,
        field_name
    ):
        """
        Load field boundary from existing
        field_polygons.xlsx
        """

        field = cls.get_field(
            field_name
        )


        if field is None:

            return None


        geojson = json.loads(
            field["GeoJSON"]
        )


        # Handle FeatureCollection

        if geojson["type"] == "FeatureCollection":

            feature = (
                geojson["features"][0]
            )

        else:

            feature = geojson


        coordinates = (
            feature["geometry"]["coordinates"][0]
        )


        points = []


        for longitude, latitude in coordinates:

            points.append(

                Coordinate(
                    latitude,
                    longitude
                )

            )


        return points
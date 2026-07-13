"""
geojson_utils.py

GeoJSON utilities for the Farm Management System.

Converts between:
- Coordinate objects
- GeoJSON
- Leaflet
- Excel storage

Author: Farm Management System GIS Engine
"""

import json
from typing import List, Dict

from .calculations import Coordinate


class GeoJSONUtils:
    """Utility methods for GeoJSON conversion."""

    @staticmethod
    def coordinates_to_geojson(
        coordinates: List[Coordinate],
        properties: Dict = None
    ) -> Dict:
        """
        Convert Coordinate objects to a GeoJSON Feature.
        """

        if not coordinates:
            raise ValueError("No coordinates supplied.")

        geojson_coords = [
            [point.longitude, point.latitude]
            for point in coordinates
        ]

        # Ensure polygon is closed
        if geojson_coords[0] != geojson_coords[-1]:
            geojson_coords.append(geojson_coords[0])

        return {
            "type": "Feature",
            "properties": properties or {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [geojson_coords]
            }
        }

    @staticmethod
    def geojson_to_coordinates(feature: Dict) -> List[Coordinate]:
        """
        Convert GeoJSON Feature back to Coordinate objects.
        """

        geometry = feature.get("geometry", {})

        if geometry.get("type") != "Polygon":
            raise ValueError("GeoJSON is not a Polygon.")

        coords = geometry["coordinates"][0]

        result = []

        for lon, lat in coords:
            result.append(
                Coordinate(
                    latitude=lat,
                    longitude=lon
                )
            )

        return result

    @staticmethod
    def feature_collection(features: List[Dict]) -> Dict:
        """
        Build a GeoJSON FeatureCollection.
        """

        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def save_geojson(filepath: str, geojson: Dict):
        """
        Save GeoJSON to disk.
        """

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(
                geojson,
                file,
                indent=4
            )

    @staticmethod
    def load_geojson(filepath: str) -> Dict:
        """
        Load GeoJSON from disk.
        """

        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def create_field_feature(
        coordinates: List[Coordinate],
        field_data: Dict
    ) -> Dict:
        """
        Creates a Farm Management System
        field GeoJSON feature.
        """

        properties = {

            "field_name":
                field_data.get(
                    "field_name"
                ),

            "estate":
                field_data.get(
                    "estate"
                ),

            "crop":
                field_data.get(
                    "crop",
                    "Sugarcane"
                ),

            "season":
                field_data.get(
                    "season"
                ),

            "area_ha":
                field_data.get(
                    "area_ha"
                ),

            "irrigation":
                field_data.get(
                    "irrigation"
                ),

            "soil_type":
                field_data.get(
                    "soil_type"
                ),

            "survey_quality":
                field_data.get(
                    "quality_score"
                )
        }


        return GeoJSONUtils.coordinates_to_geojson(
            coordinates,
            properties
        )

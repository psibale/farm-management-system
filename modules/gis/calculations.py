"""
=========================================================
Farm Management System Version 2.0
GIS Calculation Engine
=========================================================

Purpose:
    Core mathematical calculations for GIS operations.

Used by:
    - GPS Field Mapping
    - Field Boundary Management
    - Harvest Planning
    - Irrigation Planning
    - AI Farm Manager
    - Leaflet Mapping

Design:
    This module contains ONLY calculations.
    No Flask.
    No database.
    No file handling.

Author:
    Farm Management System Development Team

Version:
    2.0
=========================================================
"""

import math
import logging

from dataclasses import dataclass
from typing import List, Tuple, Optional


logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS
# =========================================================

EARTH_RADIUS_M = 6_371_000.0

METERS_PER_HECTARE = 10_000.0

METERS_PER_ACRE = 4_046.8564224

DEGREE_TO_RADIAN = math.pi / 180

RADIAN_TO_DEGREE = 180 / math.pi


# =========================================================
# DATA CLASSES
# =========================================================


@dataclass(slots=True)
class Coordinate:
    """
    Represents a GPS coordinate.

    Latitude:
        -90 to +90

    Longitude:
        -180 to +180
    """

    latitude: float
    longitude: float


    def to_tuple(self) -> Tuple[float, float]:
        """
        Convert coordinate to tuple format.

        Returns:
            (latitude, longitude)
        """

        return (
            self.latitude,
            self.longitude
        )


    def is_valid(self) -> bool:
        """
        Validate coordinate range.
        """

        return (
            -90 <= self.latitude <= 90
            and
            -180 <= self.longitude <= 180
        )



@dataclass(slots=True)
class BoundingBox:
    """
    Represents rectangular geographic limits.
    """

    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


    def contains(
        self,
        point: Coordinate
    ) -> bool:
        """
        Check if coordinate is inside box.
        """

        return (
            self.min_latitude <= point.latitude <= self.max_latitude
            and
            self.min_longitude <= point.longitude <= self.max_longitude
        )



# =========================================================
# GIS CALCULATION ENGINE
# =========================================================


class GISCalculations:
    """
    Main GIS mathematical engine.

    All GIS calculations should go through this class.
    """


    # -----------------------------------------------------
    # DISTANCE
    # -----------------------------------------------------


    @staticmethod
    def haversine_distance(
        point1: Coordinate,
        point2: Coordinate
    ) -> float:
        """
        Calculate distance between two GPS points.

        Returns:
            Distance in metres.
        """

        lat1 = math.radians(point1.latitude)
        lon1 = math.radians(point1.longitude)

        lat2 = math.radians(point2.latitude)
        lon2 = math.radians(point2.longitude)


        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1


        a = (
            math.sin(delta_lat / 2) ** 2
            +
            math.cos(lat1)
            *
            math.cos(lat2)
            *
            math.sin(delta_lon / 2) ** 2
        )


        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )


        return EARTH_RADIUS_M * c



    # -----------------------------------------------------
    # BEARING
    # -----------------------------------------------------


    @staticmethod
    def bearing(
        start: Coordinate,
        end: Coordinate
    ) -> float:
        """
        Calculate compass bearing.

        Returns:
            Degrees from North (0-360)
        """

        lat1 = math.radians(start.latitude)
        lat2 = math.radians(end.latitude)

        delta_lon = math.radians(
            end.longitude - start.longitude
        )


        x = (
            math.sin(delta_lon)
            *
            math.cos(lat2)
        )


        y = (
            math.cos(lat1)
            *
            math.sin(lat2)
            -
            math.sin(lat1)
            *
            math.cos(lat2)
            *
            math.cos(delta_lon)
        )


        bearing = math.atan2(x, y)

        bearing = math.degrees(bearing)

        return (
            bearing + 360
        ) % 360



    # -----------------------------------------------------
    # MIDPOINT
    # -----------------------------------------------------


    @staticmethod
    def midpoint(
        point1: Coordinate,
        point2: Coordinate
    ) -> Coordinate:
        """
        Calculate midpoint between two coordinates.
        """

        lat1 = math.radians(point1.latitude)
        lon1 = math.radians(point1.longitude)

        lat2 = math.radians(point2.latitude)
        lon2 = math.radians(point2.longitude)


        bx = math.cos(lat2) * math.cos(
            lon2 - lon1
        )

        by = math.cos(lat2) * math.sin(
            lon2 - lon1
        )


        lat3 = math.atan2(
            math.sin(lat1) + math.sin(lat2),
            math.sqrt(
                (math.cos(lat1) + bx)
                *
                (math.cos(lat1) + bx)
                +
                by * by
            )
        )


        lon3 = lon1 + math.atan2(
            by,
            math.cos(lat1) + bx
        )


        return Coordinate(
            latitude=math.degrees(lat3),
            longitude=math.degrees(lon3)
        )



    # -----------------------------------------------------
    # DESTINATION POINT
    # -----------------------------------------------------


    @staticmethod
    def destination_point(
        start: Coordinate,
        distance_m: float,
        bearing_deg: float
    ) -> Coordinate:
        """
        Calculate destination coordinate.

        Useful for:
            - Field navigation
            - Route planning
            - GPS tracking
        """


        angular_distance = (
            distance_m / EARTH_RADIUS_M
        )


        bearing = math.radians(
            bearing_deg
        )


        lat1 = math.radians(
            start.latitude
        )

        lon1 = math.radians(
            start.longitude
        )


        lat2 = math.asin(
            math.sin(lat1)
            *
            math.cos(angular_distance)
            +
            math.cos(lat1)
            *
            math.sin(angular_distance)
            *
            math.cos(bearing)
        )


        lon2 = (
            lon1
            +
            math.atan2(
                math.sin(bearing)
                *
                math.sin(angular_distance)
                *
                math.cos(lat1),

                math.cos(angular_distance)
                -
                math.sin(lat1)
                *
                math.sin(lat2)
            )
        )


        return Coordinate(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2)
        )
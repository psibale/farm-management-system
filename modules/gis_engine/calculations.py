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

    # -----------------------------------------------------
    # AREA CALCULATIONS
    # -----------------------------------------------------

    @staticmethod
    def polygon_area(
        points: List[Coordinate]
    ) -> float:
        """
        Calculate polygon area in square metres.

        Uses a spherical approximation suitable
        for agricultural field boundaries.

        Returns:
            Area in square metres.
        """

        if len(points) < 3:
            return 0.0


        # Convert coordinates to radians

        area = 0.0

        for i in range(len(points)):

            j = (i + 1) % len(points)

            lat1 = math.radians(
                points[i].latitude
            )

            lat2 = math.radians(
                points[j].latitude
            )

            lon_diff = math.radians(
                points[j].longitude
                -
                points[i].longitude
            )


            area += (
                lon_diff
                *
                (
                    2
                    +
                    math.sin(lat1)
                    +
                    math.sin(lat2)
                )
            )


        area = abs(area)

        area *= (
            EARTH_RADIUS_M
            *
            EARTH_RADIUS_M
            /
            2
        )


        return area



    @staticmethod
    def square_metres_to_hectares(
        area_m2: float
    ) -> float:
        """
        Convert square metres to hectares.
        """

        return area_m2 / METERS_PER_HECTARE



    @staticmethod
    def hectares_to_acres(
        hectares: float
    ) -> float:
        """
        Convert hectares to acres.
        """

        return (
            hectares
            *
            2.47105
        )



    @staticmethod
    def acres_to_hectares(
        acres: float
    ) -> float:
        """
        Convert acres to hectares.
        """

        return (
            acres
            /
            2.47105
        )



    # -----------------------------------------------------
    # PERIMETER
    # -----------------------------------------------------


    @staticmethod
    def polygon_perimeter(
        points: List[Coordinate]
    ) -> float:
        """
        Calculate field boundary length.

        Returns:
            Perimeter in metres.
        """

        if len(points) < 2:
            return 0.0


        perimeter = 0.0


        for i in range(len(points)):

            next_point = (
                i + 1
            ) % len(points)


            perimeter += (
                GISCalculations.haversine_distance(
                    points[i],
                    points[next_point]
                )
            )


        return perimeter



    # -----------------------------------------------------
    # CENTROID
    # -----------------------------------------------------


    @staticmethod
    def polygon_centroid(
        points: List[Coordinate]
    ) -> Optional[Coordinate]:
        """
        Calculate polygon centre point.

        Used for:
            - Map labels
            - Weather lookup
            - Satellite queries
        """

        if len(points) < 3:
            return None


        latitude = sum(
            p.latitude
            for p in points
        ) / len(points)


        longitude = sum(
            p.longitude
            for p in points
        ) / len(points)


        return Coordinate(
            latitude,
            longitude
        )



    # -----------------------------------------------------
    # BOUNDING BOX
    # -----------------------------------------------------


    @staticmethod
    def bounding_box(
        points: List[Coordinate]
    ) -> Optional[BoundingBox]:
        """
        Calculate rectangular limits
        around a field.
        """

        if not points:
            return None


        latitudes = [
            p.latitude
            for p in points
        ]


        longitudes = [
            p.longitude
            for p in points
        ]


        return BoundingBox(
            min_latitude=min(latitudes),
            max_latitude=max(latitudes),
            min_longitude=min(longitudes),
            max_longitude=max(longitudes)
        )



    # -----------------------------------------------------
    # FIELD MEASUREMENTS
    # -----------------------------------------------------


    @staticmethod
    def field_measurements(
        points: List[Coordinate]
    ) -> dict:
        """
        Generate complete field measurements.

        Used by:
            - GIS dashboard
            - Field registration
            - Reports
        """

        area_m2 = (
            GISCalculations.polygon_area(points)
        )


        area_ha = (
            GISCalculations.square_metres_to_hectares(
                area_m2
            )
        )


        perimeter = (
            GISCalculations.polygon_perimeter(points)
        )


        centroid = (
            GISCalculations.polygon_centroid(points)
        )


        return {

            "point_count": len(points),

            "area_m2": round(
                area_m2,
                2
            ),

            "area_ha": round(
                area_ha,
                4
            ),

            "area_acres": round(
                GISCalculations.hectares_to_acres(
                    area_ha
                ),
                4
            ),

            "perimeter_m": round(
                perimeter,
                2
            ),

            "centroid": (
                centroid.to_tuple()
                if centroid
                else None
            )

        }

    # -----------------------------------------------------
    # FIELD SHAPE ANALYSIS
    # -----------------------------------------------------

    @staticmethod
    def field_dimensions(
        points: List[Coordinate]
    ) -> dict:
        """
        Estimate field length and width.

        Useful for:
            - Irrigation layout
            - Harvest planning
            - Access planning
        """

        if len(points) < 2:
            return {
                "length_m": 0,
                "width_m": 0
            }


        max_distance = 0
        min_distance = float("inf")


        for i in range(len(points)):

            for j in range(
                i + 1,
                len(points)
            ):

                distance = (
                    GISCalculations.haversine_distance(
                        points[i],
                        points[j]
                    )
                )


                max_distance = max(
                    max_distance,
                    distance
                )

                min_distance = min(
                    min_distance,
                    distance
                )


        return {

            "length_m": round(
                max_distance,
                2
            ),

            "width_m": round(
                min_distance,
                2
            )

        }



    # -----------------------------------------------------
    # COMPACTNESS
    # -----------------------------------------------------

    @staticmethod
    def compactness(
        points: List[Coordinate]
    ) -> float:
        """
        Calculate field compactness.

        Value:
            1.0 = perfect circle
            Lower values = irregular shape

        Useful for:
            Harvest efficiency analysis
        """

        area = (
            GISCalculations.polygon_area(points)
        )


        perimeter = (
            GISCalculations.polygon_perimeter(points)
        )


        if perimeter == 0:
            return 0


        compactness = (
            4
            *
            math.pi
            *
            area
            /
            (
                perimeter ** 2
            )
        )


        return round(
            compactness,
            4
        )



    # -----------------------------------------------------
    # POLYGON ORIENTATION
    # -----------------------------------------------------

    @staticmethod
    def polygon_orientation(
        points: List[Coordinate]
    ) -> str:
        """
        Determine polygon direction.

        Returns:

            Clockwise

            Counter-clockwise
        """

        if len(points) < 3:
            return "Unknown"


        total = 0


        for i in range(len(points)):

            j = (
                i + 1
            ) % len(points)


            total += (
                (
                    points[j].longitude
                    -
                    points[i].longitude
                )
                *
                (
                    points[j].latitude
                    +
                    points[i].latitude
                )
            )


        if total > 0:
            return "Clockwise"

        return "Counter-clockwise"



    # -----------------------------------------------------
    # DISTANCE MATRIX
    # -----------------------------------------------------

    @staticmethod
    def distance_matrix(
        points: List[Coordinate]
    ) -> List[List[float]]:
        """
        Calculate distance between
        every point in a polygon.

        Useful for:
            - GPS quality checking
            - Route planning
        """

        matrix = []


        for point_a in points:

            row = []

            for point_b in points:

                row.append(
                    round(
                        GISCalculations
                        .haversine_distance(
                            point_a,
                            point_b
                        ),
                        2
                    )
                )

            matrix.append(row)


        return matrix



    # -----------------------------------------------------
    # NEAREST POINT
    # -----------------------------------------------------

    @staticmethod
    def nearest_point(
        target: Coordinate,
        points: List[Coordinate]
    ) -> Optional[Coordinate]:
        """
        Find closest GPS point.
        """

        if not points:
            return None


        nearest = None
        shortest_distance = float("inf")


        for point in points:

            distance = (
                GISCalculations
                .haversine_distance(
                    target,
                    point
                )
            )


            if distance < shortest_distance:

                shortest_distance = distance
                nearest = point


        return nearest



    # -----------------------------------------------------
    # POINT TO LINE DISTANCE
    # -----------------------------------------------------

    @staticmethod
    def point_distance_from_line(
        point: Coordinate,
        line_start: Coordinate,
        line_end: Coordinate
    ) -> float:
        """
        Approximate distance from a point
        to a line segment.

        Used by:
            Polygon simplification
        """

        x = point.longitude
        y = point.latitude


        x1 = line_start.longitude
        y1 = line_start.latitude


        x2 = line_end.longitude
        y2 = line_end.latitude


        numerator = abs(
            (
                y2 - y1
            )
            *
            x
            -
            (
                x2 - x1
            )
            *
            y
            +
            x2*y1
            -
            y2*x1
        )


        denominator = math.sqrt(
            (
                y2-y1
            )**2
            +
            (
                x2-x1
            )**2
        )


        if denominator == 0:
            return 0


        distance_degree = (
            numerator
            /
            denominator
        )


        return (
            distance_degree
            *
            111320
        )
    # -----------------------------------------------------
    # REMOVE DUPLICATE POINTS
    # -----------------------------------------------------

    @staticmethod
    def remove_duplicate_points(
        points: List[Coordinate]
    ) -> List[Coordinate]:
        """
        Remove identical consecutive GPS points.
        """

        if not points:
            return []


        cleaned = [points[0]]


        for point in points[1:]:

            previous = cleaned[-1]


            if (
                point.latitude != previous.latitude
                or
                point.longitude != previous.longitude
            ):
                cleaned.append(point)


        return cleaned



    # -----------------------------------------------------
    # REMOVE GPS NOISE
    # -----------------------------------------------------

    @staticmethod
    def remove_gps_noise(
        points: List[Coordinate],
        minimum_distance_m: float = 1.0
    ) -> List[Coordinate]:
        """
        Remove points that are too close together.

        Useful when GPS records every second
        while standing still.
        """

        if not points:
            return []


        filtered = [
            points[0]
        ]


        last_point = points[0]


        for point in points[1:]:

            distance = (
                GISCalculations
                .haversine_distance(
                    last_point,
                    point
                )
            )


            if distance >= minimum_distance_m:

                filtered.append(point)
                last_point = point


        return filtered



    # -----------------------------------------------------
    # CLOSE POLYGON
    # -----------------------------------------------------

    @staticmethod
    def close_polygon(
        points: List[Coordinate]
    ) -> List[Coordinate]:
        """
        Ensure polygon starts and ends
        at the same point.
        """

        if len(points) < 3:
            return points


        if (
            points[0].latitude
            !=
            points[-1].latitude
            or
            points[0].longitude
            !=
            points[-1].longitude
        ):

            points.append(
                points[0]
            )


        return points



    # -----------------------------------------------------
    # RDP POLYGON SIMPLIFICATION
    # -----------------------------------------------------

    @staticmethod
    def simplify_polygon(
        points: List[Coordinate],
        tolerance_m: float = 5
    ) -> List[Coordinate]:
        """
        Reduce unnecessary GPS points.

        Example:

        Before:
            500 GPS points

        After:
            60 important points

        Keeps field shape but reduces storage.
        """


        if len(points) <= 3:
            return points



        def simplify(
            pts
        ):

            if len(pts) <= 2:
                return pts


            start = pts[0]
            end = pts[-1]


            max_distance = 0
            index = 0


            for i in range(
                1,
                len(pts)-1
            ):

                distance = (
                    GISCalculations
                    .point_distance_from_line(
                        pts[i],
                        start,
                        end
                    )
                )


                if distance > max_distance:

                    max_distance = distance
                    index = i



            if max_distance > tolerance_m:

                left = simplify(
                    pts[:index+1]
                )

                right = simplify(
                    pts[index:]
                )


                return (
                    left[:-1]
                    +
                    right
                )


            return [
                start,
                end
            ]



        return simplify(points)



    # -----------------------------------------------------
    # CLEAN FIELD GPS DATA
    # -----------------------------------------------------

    @staticmethod
    def clean_boundary(
        points: List[Coordinate],
        tolerance_m: float = 5
    ) -> List[Coordinate]:
        """
        Complete GPS cleaning pipeline.

        Processing order:

        1. Remove duplicates
        2. Remove GPS noise
        3. Simplify polygon
        4. Close boundary
        """

        points = (
            GISCalculations
            .remove_duplicate_points(points)
        )


        points = (
            GISCalculations
            .remove_gps_noise(points)
        )


        points = (
            GISCalculations
            .simplify_polygon(
                points,
                tolerance_m
            )
        )


        points = (
            GISCalculations
            .close_polygon(points)
        )


        return points



    # -----------------------------------------------------
    # SURVEY QUALITY SCORE
    # -----------------------------------------------------

    @staticmethod
    def survey_quality(
        points: List[Coordinate]
    ) -> dict:
        """
        Estimate GPS survey quality.

        Returns score for field mapping.
        """

        score = 100

        warnings = []


        if len(points) < 3:

            return {

                "score": 0,

                "status": "Invalid",

                "warnings": [
                    "Not enough points"
                ]

            }



        if len(points) > 200:

            score -= 10

            warnings.append(
                "Too many GPS points"
            )



        area = (
            GISCalculations
            .polygon_area(points)
        )


        if area < 100:

            score -= 20

            warnings.append(
                "Field area unusually small"
            )



        perimeter = (
            GISCalculations
            .polygon_perimeter(points)
        )


        if perimeter > 0:

            compactness = (
                4
                *
                math.pi
                *
                area
                /
                perimeter**2
            )


            if compactness < 0.2:

                score -= 15

                warnings.append(
                    "Very irregular field shape"
                )



        return {

            "score": max(score,0),

            "status":
                (
                    "Excellent"
                    if score >= 90
                    else
                    "Good"
                    if score >= 70
                    else
                    "Needs Review"
                ),

            "warnings": warnings

        }

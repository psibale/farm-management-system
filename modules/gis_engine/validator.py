"""
=========================================================
Farm Management System Version 2.0
GIS Validation Engine
=========================================================

Purpose:
    Validates GPS field surveys before they are
    saved to the database.

Responsibilities:
    • Coordinate validation
    • Polygon validation
    • GPS quality validation
    • Agricultural business rules
    • Survey completeness

Author:
    Peter Sibale

Version:
    2.0
=========================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict

from .calculations import (
    Coordinate,
    GISCalculations
)

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """
    Result returned by every validation.
    """

    valid: bool = True

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    info: List[str] = field(default_factory=list)

    def add_error(self, message: str):

        self.valid = False

        self.errors.append(message)

    def add_warning(self, message: str):

        self.warnings.append(message)

    def add_info(self, message: str):

        self.info.append(message)

@dataclass
class ValidationReport:
    """
    Complete GIS survey validation report.
    """

    valid: bool = True

    field_area_ha: float = 0.0

    perimeter_m: float = 0.0

    point_count: int = 0

    compactness: float = 0.0

    quality_score: int = 0

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    info: List[str] = field(default_factory=list)


    def to_dict(self) -> Dict:
        """
        Convert report to JSON format.
        """

        return {

            "valid": self.valid,

            "field_area_ha": round(
                self.field_area_ha,
                2
            ),

            "perimeter_m": round(
                self.perimeter_m,
                2
            ),

            "point_count": self.point_count,

            "compactness": round(
                self.compactness,
                2
            ),

            "quality_score": self.quality_score,

            "errors": self.errors,

            "warnings": self.warnings,

            "info": self.info
        }

class GISValidator:
    """
    Enterprise GIS validation engine.
    """

    MIN_POINTS = 3

    MAX_POINTS = 1000

    MIN_FIELD_SIZE_HA = 0.05

    MAX_FIELD_SIZE_HA = 1000

    MAX_GPS_ACCURACY_M = 20

    @classmethod
    def validate_coordinates(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()

        if not points:

            result.add_error(
                "No GPS coordinates supplied."
            )

            return result

        for index, point in enumerate(points[:-1], start=1):

            if not point.is_valid():

                result.add_error(
                    f"Point {index} contains invalid latitude or longitude."
                )

        return result

    @classmethod
    def validate_point_count(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()

        if len(points) < cls.MIN_POINTS:

            result.add_error(
                f"A field boundary requires at least "
                f"{cls.MIN_POINTS} GPS points."
            )

        if len(points) > cls.MAX_POINTS:

            result.add_warning(
                f"Survey contains {len(points)} points. "
                "Consider simplifying the boundary."
            )

        return result

    @classmethod
    def validate_duplicate_points(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()

        seen = set()

        for index, point in enumerate(points, start=1):

            key = (
                round(point.latitude, 7),
                round(point.longitude, 7)
            )

            if key in seen:

                result.add_warning(
                    f"Duplicate coordinate detected "
                    f"at point {index}."
                )

            seen.add(key)

        return result

    @classmethod
    def validate_country_bounds(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()

        for index, point in enumerate(points, start=1):

            if not (-18.5 <= point.latitude <= -9.0):

                result.add_error(
                    f"Point {index} is outside Malawi latitude."
                )

            if not (32.5 <= point.longitude <= 36.5):

                result.add_error(
                    f"Point {index} is outside Malawi longitude."
                )

        return result

    @classmethod
    def validate_polygon_closed(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:
        """
        Checks whether the first and last
        GPS points are the same.
        """

        result = ValidationResult()

        if len(points) < 3:
            return result


        first = points[0]
        last = points[-1]


        if (
            first.latitude != last.latitude
            or
            first.longitude != last.longitude
        ):

            result.add_warning(
                "Polygon is not closed. "
                "The system will close it automatically."
            )

        return result

    @classmethod
    def validate_field_area(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()


        area_m2 = GISCalculations.polygon_area(
            points
        )


        area_ha = (
            GISCalculations
            .square_metres_to_hectares(
                area_m2
            )
        )


        if area_ha < cls.MIN_FIELD_SIZE_HA:

            result.add_error(
                f"Field area too small: "
                f"{area_ha:.4f} ha"
            )


        if area_ha > cls.MAX_FIELD_SIZE_HA:

            result.add_error(
                f"Field area too large: "
                f"{area_ha:.2f} ha"
            )


        result.add_info(
            f"Calculated field area: "
            f"{area_ha:.2f} hectares"
        )


        return result

    @classmethod
    def validate_point_spacing(
        cls,
        points: List[Coordinate],
        minimum_distance_m: float = 1.0
    ) -> ValidationResult:

        result = ValidationResult()


        for i in range(
            len(points)-1
        ):

            distance = (
                GISCalculations
                .haversine_distance(
                    points[i],
                    points[i+1]
                )
            )


            if distance < minimum_distance_m:

                result.add_warning(
                    f"Points {i+1} and {i+2} "
                    f"are only {distance:.2f}m apart."
                )


        return result

    @classmethod
    def validate_survey_quality(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()


        if len(points) < 5:

            result.add_warning(
                "Low number of survey points. "
                "Consider walking the complete boundary."
            )


        if len(points) > 500:

            result.add_warning(
                "Large number of GPS points. "
                "Boundary simplification recommended."
            )


        return result

    @classmethod
    def validate_survey(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:
        """
        Complete GIS survey validation.

        Runs all validation rules.
        """


        final_result = ValidationResult()



        validators = [

            cls.validate_coordinates,

            cls.validate_point_count,

            cls.validate_duplicate_points,

            cls.validate_country_bounds,

            cls.validate_polygon_closed,

            cls.validate_self_intersection,

            cls.validate_field_area,

            cls.validate_point_spacing,

            cls.validate_boundary_complexity,

            cls.validate_shape_quality,

            cls.validate_survey_quality

        ]



        for validator in validators:

            result = validator(points)


            if not result.valid:

                final_result.valid = False


            final_result.errors.extend(
                result.errors
            )


            final_result.warnings.extend(
                result.warnings
            )


            final_result.info.extend(
                result.info
            )


        return final_result

    @classmethod
    def validate_self_intersection(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:
        """
        Detects if boundary lines cross each other.
        """

        result = ValidationResult()

        if len(points) < 4:
            return result


        segments = []

        for i in range(len(points) - 1):

            segments.append(
                (
                    points[i],
                    points[i + 1]
                )
            )


        for i, seg1 in enumerate(segments):

            for j, seg2 in enumerate(segments):

                # Ignore neighbouring segments
                if abs(i - j) <= 1:
                    continue

                # Ignore first and last segment
                # because they meet at polygon closure
                if (
                        i == 0 and j == len(segments) - 1
                ) or (
                        j == 0 and i == len(segments) - 1
                ):
                    continue


                if cls._segments_intersect(
                    seg1[0],
                    seg1[1],
                    seg2[0],
                    seg2[1]
                ):

                    result.add_error(
                        "Boundary self-intersection detected "
                        f"between segments {i+1} and {j+1}."
                    )

                    return result


        return result

    @staticmethod
    def _segments_intersect(
        p1,
        p2,
        p3,
        p4
    ):
        """
        Checks whether two lines cross.
        """

        def orientation(a, b, c):

            value = (
                (b.longitude - a.longitude)
                *
                (c.latitude - a.latitude)
                -
                (b.latitude - a.latitude)
                *
                (c.longitude - a.longitude)
            )


            if value > 0:
                return 1

            if value < 0:
                return -1

            return 0


        o1 = orientation(p1, p2, p3)
        o2 = orientation(p1, p2, p4)
        o3 = orientation(p3, p4, p1)
        o4 = orientation(p3, p4, p2)


        return (
            o1 != o2
            and
            o3 != o4
        )

    @classmethod
    def validate_boundary_complexity(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:

        result = ValidationResult()


        point_count = len(points)


        if point_count > 200:

            result.add_warning(
                f"Boundary contains {point_count} points. "
                "Consider simplifying."
            )


        if point_count > 500:

            result.add_error(
                "Boundary contains excessive GPS noise."
            )


        return result

    @classmethod
    def calculate_compactness(
        cls,
        points: List[Coordinate]
    ) -> float:
        """
        Measures field shape efficiency.

        1.0 = very compact shape
        Lower values = irregular shape
        """

        area = GISCalculations.polygon_area(
            points
        )

        perimeter = GISCalculations.polygon_perimeter(
            points
        )

        if perimeter == 0:
            return 0


        import math

        compactness = (
            (4 * math.pi * area)
            /
            (perimeter ** 2)
        )

        return compactness

    @classmethod
    def validate_shape_quality(
        cls,
        points: List[Coordinate]
    ) -> ValidationResult:


        result = ValidationResult()


        compactness = (
            cls.calculate_compactness(points)
        )


        if compactness < 0.25:

            result.add_warning(
                f"Irregular field shape. "
                f"Compactness score: "
                f"{compactness:.2f}"
            )


        result.add_info(
            f"Field compactness: "
            f"{compactness:.2f}"
        )


        return result

    @classmethod
    def calculate_quality_score(
        cls,
        result: ValidationResult
    ) -> int:
        """
        Calculates survey quality score.
        """

        score = 100


        score -= len(
            result.errors
        ) * 20


        score -= len(
            result.warnings
        ) * 5


        if score < 0:
            score = 0


        return score

    @classmethod
    def create_report(
        cls,
        points: List[Coordinate]
    ) -> ValidationReport:
        """
        Creates complete GIS validation report.
        """


        validation = cls.validate_survey(
            points
        )


        report = ValidationReport()


        report.valid = validation.valid


        report.point_count = len(points)


        report.errors = (
            validation.errors
        )


        report.warnings = (
            validation.warnings
        )


        report.info = (
            validation.info
        )


        area = GISCalculations.polygon_area(
            points
        )


        report.field_area_ha = (
            area / 10000
        )


        report.perimeter_m = (
            GISCalculations.polygon_perimeter(
                points
            )
        )


        report.compactness = (
            cls.calculate_compactness(
                points
            )
        )


        report.quality_score = (
            cls.calculate_quality_score(
                validation
            )
        )


        return report

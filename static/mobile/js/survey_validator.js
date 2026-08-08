/* ==========================================================
   DCGL FIELDMATE
   Survey Validator
   Version 2.0
========================================================== */

class SurveyValidator {

    //------------------------------------------------------
    // VALIDATE ENTIRE SURVEY
    //------------------------------------------------------

    static validate(survey) {

        let score = 100;

        const checks = [];

        //--------------------------------------------------
        // Survey Information
        //--------------------------------------------------

        const information =
            this.checkSurveyInformation(survey);

        checks.push(information);

        if (!information.passed)
            score -= 10;

        //--------------------------------------------------
        // GeoJSON
        //--------------------------------------------------

        const geometry =
            this.checkGeometry(survey);

        checks.push(geometry);

        if (!geometry.passed)
            score -= 30;

        //--------------------------------------------------
        // Polygon Closed
        //--------------------------------------------------

        const closed =
            this.checkPolygonClosed(survey);

        checks.push(closed);

        if (!closed.passed)
            score -= 20;

        //--------------------------------------------------
        // Minimum GPS Points
        //--------------------------------------------------

        const points =
            this.checkMinimumPoints(survey);

        checks.push(points);

        if (!points.passed)
            score -= 20;

        //--------------------------------------------------
        // Duplicate GPS Points
        //--------------------------------------------------

        const duplicates =
            this.checkDuplicatePoints(survey);

        checks.push(duplicates);

        if (!duplicates.passed)
            score -= 10;

        //--------------------------------------------------
        // GPS Accuracy
        //--------------------------------------------------

        const accuracy =
            this.checkAccuracy(survey);

        checks.push(accuracy);

        score -= accuracy.penalty;

        //--------------------------------------------------
        // Area
        //--------------------------------------------------

        const area =
            this.checkArea(survey);

        checks.push(area);

        if (!area.passed)
            score -= 20;

        //--------------------------------------------------
        // Perimeter
        //--------------------------------------------------

        const perimeter =
            this.checkPerimeter(survey);

        checks.push(perimeter);

        if (!perimeter.passed)
            score -= 10;

        //--------------------------------------------------
        // Distance Walked
        //--------------------------------------------------

        const distance =
            this.checkDistance(survey);

        checks.push(distance);

        if (!distance.passed)
            score -= 5;

        //--------------------------------------------------
        // Parent Area
        //--------------------------------------------------

        if (survey.survey_type === "Sub-field") {

            const parent =
                this.checkParentArea(survey);

            checks.push(parent);

            if (!parent.passed)
                score -= 20;

        }

        //--------------------------------------------------
        // Never below zero
        //--------------------------------------------------

        score = Math.max(score, 0);

        //--------------------------------------------------
        // Overall Status
        //--------------------------------------------------

        let status;

        if (score >= 90) {

            status = "EXCELLENT";

        }

        else if (score >= 80) {

            status = "GOOD";

        }

        else if (score >= 70) {

            status = "ACCEPTABLE";

        }

        else {

            status = "REVIEW REQUIRED";

        }

        return {

            passed: score >= 70,

            score: score,

            status: status,

            checks: checks

        };

    }


    //------------------------------------------------------
    // SURVEY INFORMATION
    //------------------------------------------------------

    static checkSurveyInformation(survey) {

        const required = [

            "survey_type",
            "field",
            "season",
            "surveyor"

        ];

        const missing = [];

        required.forEach(field => {

            if (
                survey[field] === undefined ||
                survey[field] === null ||
                String(survey[field]).trim() === ""
            ) {

                missing.push(field);

            }

        });

        if (missing.length > 0) {

            return {

                name: "Survey Information",

                passed: false,

                message:
                    "Missing: " +
                    missing.join(", "),

                penalty: 10

            };

        }

        return {

            name: "Survey Information",

            passed: true,

            message: "Survey information complete.",

            penalty: 0

        };

    }


    //------------------------------------------------------
    // GEOMETRY
    //------------------------------------------------------

    static checkGeometry(survey) {

        if (!survey.geojson) {

            return {

                name: "Polygon Geometry",

                passed: false,

                message: "No GeoJSON polygon found."

            };

        }

        if (
            !survey.geojson.geometry ||
            survey.geojson.geometry.type !== "Polygon"
        ) {

            return {

                name: "Polygon Geometry",

                passed: false,

                message: "Invalid polygon geometry."

            };

        }

        const coordinates =
            survey.geojson.geometry.coordinates;

        if (
            !Array.isArray(coordinates) ||
            coordinates.length === 0
        ) {

            return {

                name: "Polygon Geometry",

                passed: false,

                message: "Polygon has no coordinates."

            };

        }

        return {

            name: "Polygon Geometry",

            passed: true,

            message: "Valid polygon geometry."

        };

    }


    //------------------------------------------------------
    // POLYGON CLOSED
    //------------------------------------------------------

    static checkPolygonClosed(survey) {

        if (!survey.geojson) {

            return {

                name: "Polygon Closed",

                passed: false,

                message: "No polygon available."

            };

        }

        try {

            const coordinates =
                survey.geojson.geometry.coordinates[0];

            if (
                !coordinates ||
                coordinates.length < 3
            ) {

                return {

                    name: "Polygon Closed",

                    passed: false,

                    message: "Insufficient polygon coordinates."

                };

            }

            const first =
                coordinates[0];

            const last =
                coordinates[coordinates.length - 1];

            const closed =
                first[0] === last[0] &&
                first[1] === last[1];

            return {

                name: "Polygon Closed",

                passed: closed,

                message: closed
                    ? "Boundary properly closed."
                    : "Boundary is not closed."

            };

        }

        catch (error) {

            return {

                name: "Polygon Closed",

                passed: false,

                message: "Unable to verify polygon closure."

            };

        }

    }


    //------------------------------------------------------
    // GPS POINTS
    //------------------------------------------------------

    static checkMinimumPoints(survey) {

        const count =
            Number(survey.points || 0);

        if (count >= 20) {

            return {

                name: "GPS Points",

                passed: true,

                message:
                    count +
                    " GPS points recorded."

            };

        }

        return {

            name: "GPS Points",

            passed: false,

            message:
                count +
                " GPS points. Minimum recommended: 20."

        };

    }


    //------------------------------------------------------
    // DUPLICATE POINTS
    //------------------------------------------------------

    static checkDuplicatePoints(survey) {

        try {

            if (!survey.geojson) {

                return {

                    name: "Duplicate Points",

                    passed: false,

                    message: "No polygon available."

                };

            }

            const coordinates =
                survey.geojson.geometry.coordinates[0];

            if (!coordinates) {

                return {

                    name: "Duplicate Points",

                    passed: false,

                    message: "No coordinates available."

                };

            }

            const seen = new Set();

            let duplicates = 0;

            coordinates.forEach(point => {

                const key =
                    Number(point[0]).toFixed(7) +
                    "," +
                    Number(point[1]).toFixed(7);

                if (seen.has(key)) {

                    duplicates++;

                }

                else {

                    seen.add(key);

                }

            });

            if (duplicates === 0) {

                return {

                    name: "Duplicate Points",

                    passed: true,

                    message: "No duplicate coordinates."

                };

            }

            return {

                name: "Duplicate Points",

                passed: false,

                message:
                    duplicates +
                    " duplicate coordinate(s) detected."

            };

        }

        catch (error) {

            return {

                name: "Duplicate Points",

                passed: false,

                message:
                    "Unable to check coordinates."

            };

        }

    }


    //------------------------------------------------------
    // GPS ACCURACY
    //------------------------------------------------------

    static checkAccuracy(survey) {

        const accuracy =
            Number(
                survey.average_accuracy || 0
            );

        let penalty = 0;

        let passed = true;

        let message = "";

        if (accuracy <= 3) {

            message =
                "Excellent (" +
                accuracy.toFixed(1) +
                " m)";

        }

        else if (accuracy <= 5) {

            penalty = 5;

            message =
                "Good (" +
                accuracy.toFixed(1) +
                " m)";

        }

        else if (accuracy <= 10) {

            penalty = 10;

            message =
                "Fair (" +
                accuracy.toFixed(1) +
                " m)";

        }

        else {

            penalty = 20;

            passed = false;

            message =
                "Poor (" +
                accuracy.toFixed(1) +
                " m)";

        }

        return {

            name: "GPS Accuracy",

            passed: passed,

            penalty: penalty,

            message: message

        };

    }


    //------------------------------------------------------
    // AREA
    //------------------------------------------------------

    static checkArea(survey) {

        const area =
            Number(survey.area || 0);

        if (area > 0) {

            return {

                name: "Survey Area",

                passed: true,

                message:
                    area.toFixed(3) +
                    " ha calculated."

            };

        }

        return {

            name: "Survey Area",

            passed: false,

            message:
                "Survey area is zero or invalid."

        };

    }


    //------------------------------------------------------
    // PERIMETER
    //------------------------------------------------------

    static checkPerimeter(survey) {

        const perimeter =
            Number(survey.perimeter || 0);

        if (perimeter > 0) {

            return {

                name: "Survey Perimeter",

                passed: true,

                message:
                    perimeter.toFixed(1) +
                    " m calculated."

            };

        }

        return {

            name: "Survey Perimeter",

            passed: false,

            message:
                "Perimeter is zero or invalid."

        };

    }


    //------------------------------------------------------
    // DISTANCE WALKED
    //------------------------------------------------------

    static checkDistance(survey) {

        const distance =
            Number(survey.distance || 0);

        if (distance > 0) {

            return {

                name: "Distance Walked",

                passed: true,

                message:
                    distance.toFixed(1) +
                    " m walked."

            };

        }

        return {

            name: "Distance Walked",

            passed: false,

            message:
                "No walking distance recorded."

        };

    }


    //------------------------------------------------------
    // PARENT AREA
    //------------------------------------------------------

    static checkParentArea(survey) {

        if (
            survey.remaining_area === undefined ||
            survey.remaining_area === null
        ) {

            return {

                name: "Parent Area",

                passed: true,

                message:
                    "Parent area not available for validation."

            };

        }

        const surveyArea =
            Number(survey.area || 0);

        const remainingArea =
            Number(survey.remaining_area || 0);

        if (surveyArea > remainingArea) {

            return {

                name: "Parent Area",

                passed: false,

                message:
                    "Survey area exceeds remaining parent area."

            };

        }

        return {

            name: "Parent Area",

            passed: true,

            message:
                "Remaining parent area is sufficient."

        };

    }

}


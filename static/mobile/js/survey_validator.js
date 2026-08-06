/* ==========================================================
   DCGL FIELDMATE
   Survey Validator
   Version 1.0
========================================================== */

class SurveyValidator {

    //------------------------------------------------------
    // VALIDATE ENTIRE SURVEY
    //------------------------------------------------------

    static validate(survey) {

        let score = 100;

        const checks = [];

        //--------------------------------------------------
        // Polygon Closed
        //--------------------------------------------------

        const closed = this.checkPolygonClosed(survey);

        checks.push(closed);

        if (!closed.passed)
            score -= 30;

        //--------------------------------------------------
        // Minimum GPS Points
        //--------------------------------------------------

        const points = this.checkMinimumPoints(survey);

        checks.push(points);

        if (!points.passed)
            score -= 20;

        //--------------------------------------------------
        // Duplicate GPS Points
        //--------------------------------------------------

        const duplicates = this.checkDuplicatePoints(survey);

        checks.push(duplicates);

        if (!duplicates.passed)
            score -= 10;

        //--------------------------------------------------
        // GPS Accuracy
        //--------------------------------------------------

        const accuracy = this.checkAccuracy(survey);

        checks.push(accuracy);

        score -= accuracy.penalty;

        //--------------------------------------------------
        // Parent Area
        //--------------------------------------------------

        if (survey.survey_type === "Sub-field") {

            const parent = this.checkParentArea(survey);

            checks.push(parent);

            if (!parent.passed)
                score -= 20;

        }

        //--------------------------------------------------
        // Never below zero
        //--------------------------------------------------

        if (score < 0)
            score = 0;

        return {

            passed: score >= 70,

            score: score,

            checks: checks

        };

    }

    //------------------------------------------------------
    // POLYGON CLOSED
    //------------------------------------------------------

    static checkPolygonClosed(survey) {

        const polygon = survey.geojson;

        if (!polygon)
            return {

                name: "Polygon",

                passed: false,

                message: "No polygon."

            };

        return {

            name: "Polygon Closed",

            passed: true,

            message: "Boundary closed."

        };

    }

    //------------------------------------------------------
    // GPS POINTS
    //------------------------------------------------------

    static checkMinimumPoints(survey) {

        const count = survey.points || 0;

        return {

            name: "GPS Points",

            passed: count >= 20,

            message: count + " GPS points."

        };

    }

    //------------------------------------------------------
    // DUPLICATES
    //------------------------------------------------------

    static checkDuplicatePoints(survey) {

        if (!survey.geojson)
            return {

                name: "Duplicate Points",

                passed: true,

                message: "Unknown."

            };

        const coords = survey.geojson.geometry.coordinates[0];

        const seen = new Set();

        for (const point of coords) {

            const key =
                point[0].toFixed(7) +
                "," +
                point[1].toFixed(7);

            if (seen.has(key)) {

                return {

                    name: "Duplicate Points",

                    passed: false,

                    message: "Duplicate coordinate found."

                };

            }

            seen.add(key);

        }

        return {

            name: "Duplicate Points",

            passed: true,

            message: "No duplicates."

        };

    }

    //------------------------------------------------------
    // GPS ACCURACY
    //------------------------------------------------------

    static checkAccuracy(survey) {

        const accuracy = Number(survey.average_accuracy || 0);

        let penalty = 0;

        let passed = true;

        let message = "";

        if (accuracy <= 3) {

            message = "Excellent (" + accuracy.toFixed(1) + " m)";

        }

        else if (accuracy <= 5) {

            penalty = 5;

            message = "Good (" + accuracy.toFixed(1) + " m)";

        }

        else if (accuracy <= 10) {

            penalty = 10;

            message = "Fair (" + accuracy.toFixed(1) + " m)";

        }

        else {

            penalty = 20;

            passed = false;

            message = "Poor (" + accuracy.toFixed(1) + " m)";

        }

        return {

            name: "GPS Accuracy",

            passed: passed,

            penalty: penalty,

            message: message

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

                message: "Not checked."

            };

        }

        if (survey.area > survey.remaining_area) {

            return {

                name: "Parent Area",

                passed: false,

                message: "Survey exceeds remaining parent area."

            };

        }

        return {

            name: "Parent Area",

            passed: true,

            message: "Remaining area sufficient."

        };

    }

}
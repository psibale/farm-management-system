/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Database
   Version 4.0

   FEATURES
   ----------------------------------------------------------
   - Offline survey queue
   - Survey synchronization status
   - Local FieldMate user profile
   - Local survey configuration
   - Offline Survey Details
   - Persistent GPS survey points
   - GPS recording survives page reload
   - IndexedDB persistence
========================================================== */


const DCGL_OFFLINE_DB =
    "DCGL_FieldMate_DB";


const DCGL_OFFLINE_VERSION =
    4;


const DCGL_OFFLINE_STORE =
    "surveyQueue";


const DCGL_APP_STORE =
    "fieldmateApp";


const DCGL_GPS_STORE =
    "gpsPoints";


// ==========================================================
// OPEN DATABASE
// ==========================================================

function openOfflineDatabase() {

    return new Promise((resolve, reject) => {

        const request =
            indexedDB.open(
                DCGL_OFFLINE_DB,
                DCGL_OFFLINE_VERSION
            );


        // --------------------------------------------------
        // DATABASE UPGRADE
        // --------------------------------------------------

        request.onupgradeneeded =
            function(event) {

                const db =
                    event.target.result;

                let store;


                // ==================================================
                // SURVEY QUEUE
                // ==================================================

                if (
                    !db.objectStoreNames.contains(
                        DCGL_OFFLINE_STORE
                    )
                ) {

                    store =
                        db.createObjectStore(
                            DCGL_OFFLINE_STORE,
                            {
                                keyPath:
                                    "survey_id"
                            }
                        );

                }

                else {

                    store =
                        event.target.transaction
                            .objectStore(
                                DCGL_OFFLINE_STORE
                            );

                }


                // --------------------------------------------------
                // SYNC STATUS INDEX
                // --------------------------------------------------

                if (
                    !store.indexNames.contains(
                        "sync_status"
                    )
                ) {

                    store.createIndex(
                        "sync_status",
                        "sync_status",
                        {
                            unique:
                                false
                        }
                    );

                }


                // --------------------------------------------------
                // CREATED DATE INDEX
                // --------------------------------------------------

                if (
                    !store.indexNames.contains(
                        "created_at"
                    )
                ) {

                    store.createIndex(
                        "created_at",
                        "created_at",
                        {
                            unique:
                                false
                        }
                    );

                }


                // --------------------------------------------------
                // FIELD INDEX
                // --------------------------------------------------

                if (
                    !store.indexNames.contains(
                        "field"
                    )
                ) {

                    store.createIndex(
                        "field",
                        "field",
                        {
                            unique:
                                false
                        }
                    );

                }


                // ==================================================
                // FIELDMATE APPLICATION STORE
                // ==================================================

                if (
                    !db.objectStoreNames.contains(
                        DCGL_APP_STORE
                    )
                ) {

                    db.createObjectStore(
                        DCGL_APP_STORE,
                        {
                            keyPath:
                                "key"
                        }
                    );

                }


                // ==================================================
                // GPS POINT STORE
                // ==================================================
                //
                // Each survey has one GPS record.
                //
                // Example:
                //
                // {
                //     survey_id: "DCGL-123...",
                //     points: [...],
                //     updated_at: "..."
                // }
                //
                // This allows GPS recording to survive:
                //
                // - page refresh
                // - accidental navigation
                // - temporary browser interruption
                // - LAN disconnection
                //
                // ==================================================

                if (
                    !db.objectStoreNames.contains(
                        DCGL_GPS_STORE
                    )
                ) {

                    const gpsStore =
                        db.createObjectStore(
                            DCGL_GPS_STORE,
                            {
                                keyPath:
                                    "survey_id"
                            }
                        );


                    // --------------------------------------------------
                    // GPS UPDATED DATE INDEX
                    // --------------------------------------------------

                    gpsStore.createIndex(
                        "updated_at",
                        "updated_at",
                        {
                            unique:
                                false
                        }
                    );

                }


                console.log(
                    "=================================================="
                );

                console.log(
                    "DCGL FieldMate offline database upgraded."
                );

                console.log(
                    "Database version:",
                    DCGL_OFFLINE_VERSION
                );

                console.log(
                    "GPS point store available."
                );

                console.log(
                    "=================================================="
                );

            };


        // --------------------------------------------------
        // SUCCESS
        // --------------------------------------------------

        request.onsuccess =
            function(event) {

                const db =
                    event.target.result;


                // --------------------------------------------------
                // HANDLE FUTURE VERSION CHANGES
                // --------------------------------------------------

                db.onversionchange =
                    function() {

                        db.close();

                        console.warn(
                            "FieldMate database connection " +
                            "closed because another version " +
                            "was opened."
                        );

                    };


                resolve(db);

            };


        // --------------------------------------------------
        // ERROR
        // --------------------------------------------------

        request.onerror =
            function(event) {

                console.error(
                    "DCGL FieldMate database error:",
                    event.target.error
                );

                reject(
                    event.target.error
                );

            };


        // --------------------------------------------------
        // BLOCKED
        // --------------------------------------------------

        request.onblocked =
            function() {

                console.warn(
                    "FieldMate database upgrade is blocked. " +
                    "Close other FieldMate tabs."
                );

            };

    });

}


// ==========================================================
// CREATE UNIQUE SURVEY ID
// ==========================================================

function generateSurveyID() {

    return (

        "DCGL-" +

        Date.now() +

        "-" +

        Math.random()
            .toString(36)
            .substring(2, 10)
            .toUpperCase()

    );

}


// ==========================================================
// PREPARE SURVEY RECORD
// ==========================================================

function prepareOfflineSurvey(survey) {

    const now =
        new Date().toISOString();


    return {

        ...survey,

        survey_id:
            survey.survey_id ||
            generateSurveyID(),

        created_at:
            survey.created_at ||
            now,

        updated_at:
            now,

        sync_status:
            "pending",

        sync_attempts:
            Number(
                survey.sync_attempts || 0
            ),

        last_sync_attempt:
            survey.last_sync_attempt ||
            null,

        last_sync_error:
            survey.last_sync_error ||
            null,

        synced_at:
            survey.synced_at ||
            null

    };

}


// ==========================================================
// SAVE SURVEY OFFLINE
// ==========================================================

async function saveSurveyOffline(survey) {

    if (!survey) {

        throw new Error(
            "No survey supplied."
        );

    }


    const db =
        await openOfflineDatabase();


    const record =
        prepareOfflineSurvey(
            survey
        );


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            store.put(
                record
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "Survey saved offline:",
                        record.survey_id
                    );

                    resolve(
                        record
                    );

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };


            transaction.onabort =
                function(event) {

                    db.close();

                    reject(
                        event.target.error ||
                        new Error(
                            "Offline save transaction aborted."
                        )
                    );

                };

        }
    );

}


// ==========================================================
// SAVE FIELDMATE APPLICATION STATE
// ==========================================================

async function saveFieldMateAppData(data) {

    if (!data) {

        throw new Error(
            "No FieldMate application data supplied."
        );

    }


    const db =
        await openOfflineDatabase();


    const record = {

        key:
            "surveyData",

        data:
            data,

        saved_at:
            new Date().toISOString()

    };


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STORE
                );


            store.put(
                record
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "FieldMate application data " +
                        "saved locally."
                    );

                    resolve(
                        data
                    );

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    console.error(
                        "Unable to save FieldMate " +
                        "application data:",
                        event.target.error
                    );

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// LOAD FIELDMATE APPLICATION STATE
// ==========================================================

async function getFieldMateAppData() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STORE
                );


            const request =
                store.get(
                    "surveyData"
                );


            request.onsuccess =
                function() {

                    const record =
                        request.result;


                    resolve(
                        record
                            ? record.data
                            : null
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// SAVE FIELDMATE USER PROFILE
// ==========================================================

async function saveFieldMateUserProfile(profile) {

    if (!profile) {

        throw new Error(
            "No FieldMate user profile supplied."
        );

    }


    const db =
        await openOfflineDatabase();


    const record = {

        key:
            "userProfile",

        data:
            profile,

        saved_at:
            new Date().toISOString()

    };


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STORE
                );


            store.put(
                record
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "FieldMate user profile saved locally:",
                        profile.username
                    );

                    resolve(
                        profile
                    );

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// LOAD FIELDMATE USER PROFILE
// ==========================================================

async function getFieldMateUserProfile() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STORE
                );


            const request =
                store.get(
                    "userProfile"
                );


            request.onsuccess =
                function() {

                    const record =
                        request.result;


                    resolve(
                        record
                            ? record.data
                            : null
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// CLEAR FIELDMATE LOCAL USER DATA
// ==========================================================

async function clearFieldMateUserData() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STORE
                );


            store.delete(
                "userProfile"
            );


            store.delete(
                "surveyData"
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "FieldMate local user data cleared."
                    );

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// SAVE GPS POINTS
// ==========================================================
//
// Persists the current GPS recording locally.
//
// surveyID:
//     The unique survey identifier.
//
// points:
//     Array of GPS point objects.
//
// Example:
//
// saveGPSPoints(
//     "DCGL-12345",
//     [
//         {
//             latitude: -12.123456,
//             longitude: 34.123456,
//             accuracy: 3.2,
//             timestamp: 123456789
//         }
//     ]
// );
//
// ==========================================================

async function saveGPSPoints(
    surveyID,
    points
) {

    if (!surveyID) {

        throw new Error(
            "GPS save requires a survey ID."
        );

    }


    if (!Array.isArray(points)) {

        throw new Error(
            "GPS points must be an array."
        );

    }


    const db =
        await openOfflineDatabase();


    const record = {

        survey_id:
            surveyID,

        points:
            points,

        point_count:
            points.length,

        updated_at:
            new Date().toISOString()

    };


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_GPS_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_GPS_STORE
                );


            store.put(
                record
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "GPS points saved locally:",
                        surveyID,
                        points.length
                    );

                    resolve(
                        record
                    );

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    console.error(
                        "Unable to save GPS points:",
                        event.target.error
                    );

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// LOAD GPS POINTS
// ==========================================================

async function getGPSPoints(
    surveyID
) {

    if (!surveyID) {

        throw new Error(
            "GPS load requires a survey ID."
        );

    }


    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_GPS_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_GPS_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    const record =
                        request.result;


                    resolve(
                        record
                            ? record.points
                            : []
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// GET COMPLETE GPS RECORD
// ==========================================================

async function getGPSRecord(
    surveyID
) {

    if (!surveyID) {

        throw new Error(
            "GPS record requires a survey ID."
        );

    }


    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_GPS_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_GPS_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    resolve(
                        request.result ||
                        null
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// DELETE GPS POINTS
// ==========================================================

async function deleteGPSPoints(
    surveyID
) {

    if (!surveyID) {

        throw new Error(
            "GPS delete requires a survey ID."
        );

    }


    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_GPS_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_GPS_STORE
                );


            store.delete(
                surveyID
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "GPS points deleted:",
                        surveyID
                    );

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// GET ALL GPS RECORDS
// ==========================================================

async function getAllGPSRecords() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_GPS_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_GPS_STORE
                );


            const request =
                store.getAll();


            request.onsuccess =
                function() {

                    resolve(
                        request.result || []
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// GET ALL PENDING SURVEYS
// ==========================================================

async function getPendingSurveys() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const index =
                store.index(
                    "sync_status"
                );


            const request =
                index.getAll(
                    "pending"
                );


            request.onsuccess =
                function() {

                    resolve(
                        request.result || []
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// GET ALL OFFLINE SURVEYS
// ==========================================================

async function getAllOfflineSurveys() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const request =
                store.getAll();


            request.onsuccess =
                function() {

                    resolve(
                        request.result || []
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// GET ONE SURVEY
// ==========================================================

async function getOfflineSurvey(
    surveyID
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    resolve(
                        request.result ||
                        null
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                };

        }
    );

}


// ==========================================================
// MARK SURVEY AS SYNCED
// ==========================================================

async function markSurveySynced(
    surveyID
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    const survey =
                        request.result;


                    if (!survey) {

                        return;

                    }


                    survey.sync_status =
                        "synced";


                    survey.synced_at =
                        new Date().toISOString();


                    survey.last_sync_error =
                        null;


                    store.put(
                        survey
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// DELETE SYNCHRONIZED SURVEY
// ==========================================================

async function deleteOfflineSurvey(
    surveyID
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            store.delete(
                surveyID
            );


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "Offline survey removed:",
                        surveyID
                    );

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// MARK SURVEY AS FAILED
// ==========================================================

async function markSurveyFailed(
    surveyID,
    errorMessage
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    const survey =
                        request.result;


                    if (!survey) {

                        return;

                    }


                    survey.sync_status =
                        "pending";


                    survey.sync_attempts =
                        Number(
                            survey.sync_attempts || 0
                        ) + 1;


                    survey.last_sync_attempt =
                        new Date().toISOString();


                    survey.last_sync_error =
                        String(
                            errorMessage ||
                            "Unknown synchronization error."
                        );


                    survey.updated_at =
                        new Date().toISOString();


                    store.put(
                        survey
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// RECORD SYNC ATTEMPT
// ==========================================================

async function markSurveySyncAttempt(
    surveyID
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const request =
                store.get(
                    surveyID
                );


            request.onsuccess =
                function() {

                    const survey =
                        request.result;


                    if (!survey) {

                        resolve();

                        return;

                    }


                    survey.sync_attempts =
                        Number(
                            survey.sync_attempts || 0
                        ) + 1;


                    survey.last_sync_attempt =
                        new Date().toISOString();


                    survey.last_sync_error =
                        null;


                    store.put(
                        survey
                    );

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}


// ==========================================================
// COUNT PENDING SURVEYS
// ==========================================================

async function getPendingSurveyCount() {

    const surveys =
        await getPendingSurveys();

    return surveys.length;

}


// ==========================================================
// COUNT ALL OFFLINE SURVEYS
// ==========================================================

async function getOfflineSurveyCount() {

    const surveys =
        await getAllOfflineSurveys();

    return surveys.length;

}


// ==========================================================
// CLEAR SYNCHRONIZED SURVEYS
// ==========================================================

async function clearSyncedSurveys() {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_OFFLINE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_OFFLINE_STORE
                );


            const index =
                store.index(
                    "sync_status"
                );


            const request =
                index.openCursor(
                    "synced"
                );


            request.onsuccess =
                function(event) {

                    const cursor =
                        event.target.result;


                    if (!cursor) {

                        return;

                    }


                    cursor.delete();

                    cursor.continue();

                };


            request.onerror =
                function(event) {

                    reject(
                        event.target.error
                    );

                };


            transaction.oncomplete =
                function() {

                    db.close();

                    resolve();

                };


            transaction.onerror =
                function(event) {

                    db.close();

                    reject(
                        event.target.error
                    );

                };

        }
    );

}
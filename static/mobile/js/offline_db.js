/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Database
   Version 3.0

   FEATURES
   ----------------------------------------------------------
   - Offline survey queue
   - Offline FieldMate application state
   - Offline logged-in surveyor information
   - Sync status tracking
   - Survey metadata persistence
   - Safe database upgrades
========================================================== */


const DCGL_OFFLINE_DB =
    "DCGL_FieldMate_DB";

const DCGL_OFFLINE_STORE =
    "surveyQueue";

const DCGL_APP_STATE_STORE =
    "appState";

const DCGL_OFFLINE_VERSION =
    3;


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


        // ==================================================
        // DATABASE UPGRADE
        // ==================================================

        request.onupgradeneeded =
            function(event) {

                const db =
                    event.target.result;

                const transaction =
                    event.target.transaction;


                // ==================================================
                // SURVEY QUEUE
                // ==================================================

                let surveyStore;


                if (
                    !db.objectStoreNames.contains(
                        DCGL_OFFLINE_STORE
                    )
                ) {

                    surveyStore =
                        db.createObjectStore(
                            DCGL_OFFLINE_STORE,
                            {
                                keyPath:
                                    "survey_id"
                            }
                        );

                }

                else {

                    surveyStore =
                        transaction.objectStore(
                            DCGL_OFFLINE_STORE
                        );

                }


                // --------------------------------------------------
                // SYNC STATUS INDEX
                // --------------------------------------------------

                if (
                    !surveyStore.indexNames.contains(
                        "sync_status"
                    )
                ) {

                    surveyStore.createIndex(
                        "sync_status",
                        "sync_status",
                        {
                            unique: false
                        }
                    );

                }


                // --------------------------------------------------
                // CREATED DATE INDEX
                // --------------------------------------------------

                if (
                    !surveyStore.indexNames.contains(
                        "created_at"
                    )
                ) {

                    surveyStore.createIndex(
                        "created_at",
                        "created_at",
                        {
                            unique: false
                        }
                    );

                }


                // --------------------------------------------------
                // FIELD INDEX
                // --------------------------------------------------

                if (
                    !surveyStore.indexNames.contains(
                        "field"
                    )
                ) {

                    surveyStore.createIndex(
                        "field",
                        "field",
                        {
                            unique: false
                        }
                    );

                }


                // ==================================================
                // APPLICATION STATE STORE
                // ==================================================

                let appStore;


                if (
                    !db.objectStoreNames.contains(
                        DCGL_APP_STATE_STORE
                    )
                ) {

                    appStore =
                        db.createObjectStore(
                            DCGL_APP_STATE_STORE,
                            {
                                keyPath:
                                    "key"
                            }
                        );

                }

                else {

                    appStore =
                        transaction.objectStore(
                            DCGL_APP_STATE_STORE
                        );

                }


                console.log(
                    "DCGL FieldMate offline database upgraded to version",
                    DCGL_OFFLINE_VERSION
                );

            };


        // ==================================================
        // SUCCESS
        // ==================================================

        request.onsuccess =
            function(event) {

                const db =
                    event.target.result;


                db.onversionchange =
                    function() {

                        db.close();

                        console.warn(
                            "FieldMate database connection closed " +
                            "because another version was opened."
                        );

                    };


                resolve(db);

            };


        // ==================================================
        // ERROR
        // ==================================================

        request.onerror =
            function(event) {

                console.error(
                    "Offline database error:",
                    event.target.error
                );

                reject(
                    event.target.error
                );

            };


        // ==================================================
        // BLOCKED
        // ==================================================

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
// GENERATE UNIQUE SURVEY ID
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
            survey.last_sync_attempt || null,


        last_sync_error:
            survey.last_sync_error || null,


        synced_at:
            survey.synced_at || null

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
        prepareOfflineSurvey(survey);


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


            store.put(record);


            transaction.oncomplete =
                function() {

                    db.close();

                    console.log(
                        "Survey saved offline:",
                        record.survey_id
                    );

                    resolve(record);

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
// GET PENDING SURVEYS
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
// GET ONE OFFLINE SURVEY
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
                        request.result || null
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
// MARK SURVEY SYNCED
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

                        resolve();

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
// DELETE OFFLINE SURVEY
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
// MARK SURVEY FAILED
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


// ==========================================================
// SAVE APPLICATION STATE
// ==========================================================
//
// Used for:
// - Logged-in FieldMate user
// - Role
// - Season
// - Survey metadata
// - Parent fields
//
// ==========================================================

async function saveAppState(
    key,
    value
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STATE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STATE_STORE
                );


            store.put({

                key: key,

                value: value,

                updated_at:
                    new Date().toISOString()

            });


            transaction.oncomplete =
                function() {

                    db.close();

                    resolve(value);

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
// GET APPLICATION STATE
// ==========================================================

async function getAppState(
    key
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STATE_STORE
                    ],
                    "readonly"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STATE_STORE
                );


            const request =
                store.get(
                    key
                );


            request.onsuccess =
                function() {

                    if (
                        request.result
                    ) {

                        resolve(
                            request.result.value
                        );

                    }

                    else {

                        resolve(
                            null
                        );

                    }

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
// DELETE APPLICATION STATE
// ==========================================================

async function deleteAppState(
    key
) {

    const db =
        await openOfflineDatabase();


    return new Promise(
        (resolve, reject) => {

            const transaction =
                db.transaction(
                    [
                        DCGL_APP_STATE_STORE
                    ],
                    "readwrite"
                );


            const store =
                transaction.objectStore(
                    DCGL_APP_STATE_STORE
                );


            store.delete(
                key
            );


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
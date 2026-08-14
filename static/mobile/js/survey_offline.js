/* ==========================================================
   DCGL FIELDMATE
   Offline Survey Storage
   Version 1.0
========================================================== */

const DCGLOffline = {

    DB_NAME: "DCGL_FieldMate",
    DB_VERSION: 1,
    STORE_NAME: "pending_surveys",

    //------------------------------------------------------
    // OPEN DATABASE
    //------------------------------------------------------

    openDB() {

        return new Promise((resolve, reject) => {

            const request = indexedDB.open(
                this.DB_NAME,
                this.DB_VERSION
            );

            request.onupgradeneeded = function(event) {

                const db = event.target.result;

                if (!db.objectStoreNames.contains(
                    DCGLOffline.STORE_NAME
                )) {

                    const store = db.createObjectStore(
                        DCGLOffline.STORE_NAME,
                        {
                            keyPath: "id",
                            autoIncrement: true
                        }
                    );

                    store.createIndex(
                        "status",
                        "status",
                        { unique: false }
                    );

                    store.createIndex(
                        "created",
                        "created",
                        { unique: false }
                    );

                }

            };

            request.onsuccess = function(event) {

                resolve(event.target.result);

            };

            request.onerror = function(event) {

                console.error(
                    "IndexedDB error:",
                    event.target.error
                );

                reject(event.target.error);

            };

        });

    },


    //------------------------------------------------------
    // SAVE SURVEY OFFLINE
    //------------------------------------------------------

    async saveSurvey(survey) {

        try {

            const db = await this.openDB();

            return new Promise((resolve, reject) => {

                const transaction =
                    db.transaction(
                        this.STORE_NAME,
                        "readwrite"
                    );

                const store =
                    transaction.objectStore(
                        this.STORE_NAME
                    );

                const record = {

                    survey: survey,

                    status: "pending",

                    created:
                        new Date().toISOString(),

                    attempts: 0

                };

                const request =
                    store.add(record);

                request.onsuccess = function() {

                    console.log(
                        "Survey saved offline.",
                        request.result
                    );

                    resolve({
                        success: true,
                        id: request.result
                    });

                };

                request.onerror = function(event) {

                    console.error(
                        "Unable to save survey offline:",
                        event.target.error
                    );

                    reject(
                        event.target.error
                    );

                };

            });

        }

        catch(error) {

            console.error(
                "Offline storage error:",
                error
            );

            return {
                success: false,
                error: error
            };

        }

    },


    //------------------------------------------------------
    // GET PENDING SURVEYS
    //------------------------------------------------------

    async getPendingSurveys() {

        try {

            const db = await this.openDB();

            return new Promise((resolve, reject) => {

                const transaction =
                    db.transaction(
                        this.STORE_NAME,
                        "readonly"
                    );

                const store =
                    transaction.objectStore(
                        this.STORE_NAME
                    );

                const request =
                    store.getAll();

                request.onsuccess = function() {

                    const surveys =
                        request.result.filter(
                            item =>
                                item.status === "pending"
                        );

                    resolve(surveys);

                };

                request.onerror = function(event) {

                    reject(
                        event.target.error
                    );

                };

            });

        }

        catch(error) {

            console.error(error);

            return [];

        }

    },


    //------------------------------------------------------
    // DELETE SAVED OFFLINE SURVEY
    //------------------------------------------------------

    async deleteSurvey(id) {

        const db = await this.openDB();

        return new Promise((resolve, reject) => {

            const transaction =
                db.transaction(
                    this.STORE_NAME,
                    "readwrite"
                );

            const store =
                transaction.objectStore(
                    this.STORE_NAME
                );

            const request =
                store.delete(id);

            request.onsuccess = function() {

                resolve(true);

            };

            request.onerror = function(event) {

                reject(
                    event.target.error
                );

            };

        });

    },


    //------------------------------------------------------
    // COUNT PENDING SURVEYS
    //------------------------------------------------------

    async countPending() {

        const surveys =
            await this.getPendingSurveys();

        return surveys.length;

    }

};
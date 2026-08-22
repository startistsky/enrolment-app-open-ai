const API_URL = "http://localhost:5005";


// =========================================================
// Generic API helper
// =========================================================

async function apiRequest(
    endpoint,
    options = {}
) {

    try {

        const response = await fetch(
            `${API_URL}${endpoint}`,
            {
                ...options,

                headers: {
                    "Content-Type":
                        "application/json",

                    ...(options.headers || {})
                }
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                data.message ||
                `Request failed (${response.status})`
            );
        }

        return data;

    } catch (error) {

        console.error(
            "API error:",
            error
        );

        throw error;
    }
}


// =========================================================
// Status
// =========================================================

async function getAPIStatus() {

    return apiRequest(
        "/api/status"
    );
}


// =========================================================
// Jobs
// =========================================================

async function getJobs(params = "") {

    return apiRequest(
        `/jobs${params}`
    );
}


async function getJob(id) {

    return apiRequest(
        `/jobs/${id}`
    );
}


async function createJob(job) {

    return apiRequest(
        "/jobs",
        {
            method: "POST",

            body: JSON.stringify(job)
        }
    );
}


async function updateJob(
    id,
    job
) {

    return apiRequest(
        `/jobs/${id}`,
        {
            method: "PUT",

            body: JSON.stringify(job)
        }
    );
}


async function deleteJobAPI(id) {

    return apiRequest(
        `/jobs/${id}`,
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// Saved jobs
// =========================================================

async function saveJobAPI(id) {

    return apiRequest(
        `/saved/${id}`,
        {
            method: "POST"
        }
    );
}


async function getSavedJobs() {

    return apiRequest(
        "/saved"
    );
}


async function unsaveJobAPI(id) {

    return apiRequest(
        `/saved/${id}`,
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// Applications
// =========================================================

async function getApplications() {

    return apiRequest(
        "/applications"
    );
}


async function createApplication(
    jobId
) {

    return apiRequest(
        "/applications",
        {
            method: "POST",

            body: JSON.stringify({
                job_id: jobId,
                status: "Applied"
            })
        }
    );
}


async function updateApplication(
    id,
    status,
    notes = ""
) {

    return apiRequest(
        `/applications/${id}`,
        {
            method: "PUT",

            body: JSON.stringify({
                status,
                notes
            })
        }
    );
}


async function deleteApplicationAPI(
    id
) {

    return apiRequest(
        `/applications/${id}`,
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// Preferences
// =========================================================

async function getPreferences() {

    return apiRequest(
        "/preferences"
    );
}


async function savePreferences(
    preferences
) {

    return apiRequest(
        "/preferences",
        {
            method: "POST",

            body: JSON.stringify(
                preferences
            )
        }
    );
}


async function deletePreferences() {

    return apiRequest(
        "/preferences",
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// AI
// =========================================================

async function analyseJobAPI(id) {

    return apiRequest(
        `/jobs/${id}/analyse`,
        {
            method: "POST"
        }
    );
}


async function sendChatMessage(
    message
) {

    return apiRequest(
        "/ai/chat",
        {
            method: "POST",

            body: JSON.stringify({
                message
            })
        }
    );
}


// =========================================================
// Career Agent
// =========================================================

async function runCareerAgent() {

    return apiRequest(
        "/api/career-agent",
        {
            method: "POST"
        }
    );
}
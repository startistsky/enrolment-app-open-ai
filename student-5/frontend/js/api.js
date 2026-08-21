const API_URL = "http://localhost:5000";


async function getJobs(params = "") {

    const response = await fetch(
        `${API_URL}/jobs${params}`
    );

    return await response.json();
}


async function getJob(id) {

    const response = await fetch(
        `${API_URL}/jobs/${id}`
    );

    return await response.json();
}


async function saveJobAPI(id) {

    const response = await fetch(
        `${API_URL}/saved/${id}`,
        {
            method: "POST"
        }
    );

    return await response.json();
}


async function getSavedJobs() {

    const response = await fetch(
        `${API_URL}/saved`
    );

    return await response.json();
}


async function getApplications() {

    const response = await fetch(
        `${API_URL}/applications`
    );

    return await response.json();
}


async function createApplication(jobId) {

    const response = await fetch(
        `${API_URL}/applications`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                job_id: jobId,
                status: "Applied"
            })
        }
    );

    return await response.json();
}


async function analyseJobAPI(id) {

    const response = await fetch(
        `${API_URL}/jobs/${id}/analyse`,
        {
            method: "POST"
        }
    );

    return await response.json();
}


async function sendChatMessage(message) {

    const response = await fetch(
        `${API_URL}/ai/chat`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })
        }
    );

    return await response.json();
}
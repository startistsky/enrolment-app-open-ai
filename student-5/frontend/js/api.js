const API_URL = "http://localhost:8005/api";

async function apiRequest(url, options = {}) {
    const response = await fetch(`${API_URL}${url}`, {
        ...options,

        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    let data = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new Error(
            data.error || 
            data.detail || 
            `Request failed (${response.status})`
        );
    }

    return data;
}

// Jobs
async function getJobs(params = "") {
    return apiRequest(`/jobs${params}`);
}

async function getJob(id) {
    return apiRequest(`/jobs/${id}`);
}

async function createJobAPI(data) {
    return apiRequest("/jobs", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

async function updateJobAPI(id, data) {
    return apiRequest(`/jobs/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
}

async function deleteJobAPI(id) {
    return apiRequest(`/jobs/${id}`, {
        method: "DELETE",
    });
}

// Saved jobs
async function getSavedJobs() {
    return apiRequest("/saved");
}

async function saveJobAPI(id) {
    return apiRequest(`/saved/${id}`, {
        method: "POST",
    });
}

async function deleteSavedJobAPI(id) {
    return apiRequest(`/saved/${id}`, {
        method: "DELETE",
    });
}

// Applications
async function getApplications() {
    return apiRequest("/applications");
}

async function createApplication(jobId) {
    return apiRequest("/applications", {
        method: "POST",

        body: JSON.stringify({
            job_id: jobId,
            status: "Applied",
        }),
    });
}

async function updateApplicationAPI(id, data) {
    return apiRequest(`/applications/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
}

async function deleteApplicationAPI(id) {
    return apiRequest(`/applications/${id}`, {
        method: "DELETE",
    });
}

// AI job analysis
async function analyseJobAPI(id) {
    return apiRequest(`/jobs/${id}/analyse`, {
        method: "POST",
    });
}

//Carere Agent 
// Frontend sends the selected job id
// Backend will: 
// 1. Load the selected job 
// 2. Call MCP 
// 3. Call RAG 
// 4. Pass the retrieved information to the AI 
// 5. Return the reponse and RAG sources 
// The browser never connects directly to MCP/RAG 

async function sendChatMessage(message, jobId = null) {
    return apiRequest("/ai/chat", {
        method: "POST",

        body: JSON.stringify({
            message: message,
            job_id: jobId ? Number(jobId): null,
        }),
    });
}

// Human approval
async function submitAIApproval(approvalId, approved, feedback = "") {
    return apiRequest("/ai/approval", {
        method: "POST",

        body: JSON.stringify({
            approval_id: approvalId,
            approved: approved,
            feedback: feedback,
        }),
    });
}

// AI status
async function getAIStatus() {
    return apiRequest("/ai/status");
}

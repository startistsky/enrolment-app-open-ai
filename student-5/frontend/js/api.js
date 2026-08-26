const API_URL = "http://localhost:5005";

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
    throw new Error(data.error || "Request failed");
  }

  return data;
}

// Jobs
async function getJobs(params = "") {
  return apiRequest(`/api/jobs${params}`);
}

async function getJob(id) {
  return apiRequest(`/api/jobs/${id}`);
}

async function createJobAPI(data) {
  return apiRequest("/api/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

async function updateJobAPI(id, data) {
  return apiRequest(`/api/jobs/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

async function deleteJobAPI(id) {
  return apiRequest(`/api/jobs/${id}`, {
    method: "DELETE",
  });
}

// Saved jobs
async function getSavedJobs() {
  return apiRequest("/api/saved");
}

async function saveJobAPI(id) {
  return apiRequest(`/api/saved/${id}`, {
    method: "POST",
  });
}

async function deleteSavedJobAPI(id) {
  return apiRequest(`/api/saved/${id}`, {
    method: "DELETE",
  });
}

// Applications
async function getApplications() {
  return apiRequest("/api/applications");
}

async function createApplication(jobId) {
  return apiRequest("/api/applications", {
    method: "POST",

    body: JSON.stringify({
      job_id: jobId,
      status: "Applied",
    }),
  });
}

async function updateApplicationAPI(id, data) {
  return apiRequest(`/api/applications/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

async function deleteApplicationAPI(id) {
  return apiRequest(`/api/applications/${id}`, {
    method: "DELETE",
  });
}

// AI job analysis
async function analyseJobAPI(id) {
  return apiRequest(`/api/jobs/${id}/analyse`, {
    method: "POST",
  });
}

// AI career agent chat for a selected chat
async function sendChatMessage(message, jobId = null) {
  return apiRequest("/api/ai/chat", {
    method: "POST",

    body: JSON.stringify({
      message: message,
      job_id: jobId,
    }),
  });
}

// AI status
async function getAIStatus() {
  return apiRequest("/api/ai/status");
}

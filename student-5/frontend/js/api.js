const API_URL = "http://localhost:5005";

async function apiRequest(url, options = {}) {
  const response = await fetch(`${API_URL}${url}`, {
    ...options,

    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

// =============================
// Jobs
// =============================

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

// =============================
// Saved
// =============================

async function saveJobAPI(id) {
  return apiRequest(`/saved/${id}`, {
    method: "POST",
  });
}

async function getSavedJobs() {
  return apiRequest("/saved");
}

async function deleteSavedJobAPI(id) {
  return apiRequest(`/saved/${id}`, {
    method: "DELETE",
  });
}

// =============================
// Applications
// =============================

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

// =============================
// Career Profile
// =============================

async function getCareerProfile() {
  return apiRequest("/profile");
}

async function saveCareerProfileAPI(data) {
  return apiRequest("/profile", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// =============================
// Agent
// =============================

async function runCareerAgentAPI() {
  return apiRequest("/agent/match", {
    method: "POST",
  });
}

// =============================
// AI
// =============================

async function analyseJobAPI(id) {
  return apiRequest(`/jobs/${id}/analyse`, {
    method: "POST",
  });
}

async function sendChatMessage(message, jobId = null) {
  return apiRequest("/ai/chat", {
    method: "POST",

    body: JSON.stringify({
      message,

      job_id: jobId,
    }),
  });
}

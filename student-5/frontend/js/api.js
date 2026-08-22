const API_URL = "";

// ===============================
// Generic request
// ===============================

async function apiRequest(url, options = {}) {
  const response = await fetch(`${API_URL}${url}`, options);

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }

  return data;
}

// ===============================
// Jobs
// ===============================

async function getJobs(params = "") {
  return await apiRequest(`/jobs${params}`);
}

async function getJob(id) {
  return await apiRequest(`/jobs/${id}`);
}

async function createJobAPI(job) {
  return await apiRequest("/jobs", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(job),
  });
}

async function updateJobAPI(id, job) {
  return await apiRequest(`/jobs/${id}`, {
    method: "PUT",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(job),
  });
}

async function deleteJobAPI(id) {
  return await apiRequest(`/jobs/${id}`, {
    method: "DELETE",
  });
}

// ===============================
// Saved jobs
// ===============================

async function getSavedJobs() {
  return await apiRequest("/saved");
}

async function saveJobAPI(id) {
  return await apiRequest(`/saved/${id}`, {
    method: "POST",
  });
}

async function removeSavedJobAPI(id) {
  return await apiRequest(`/saved/${id}`, {
    method: "DELETE",
  });
}

// ===============================
// Applications
// ===============================

async function getApplications() {
  return await apiRequest("/applications");
}

async function createApplication(jobId) {
  return await apiRequest("/applications", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      job_id: jobId,
      status: "Applied",
    }),
  });
}

async function updateApplicationAPI(id, status, notes) {
  return await apiRequest(`/applications/${id}`, {
    method: "PUT",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      status,
      notes,
    }),
  });
}

async function deleteApplicationAPI(id) {
  return await apiRequest(`/applications/${id}`, {
    method: "DELETE",
  });
}

// ===============================
// Preferences
// ===============================

async function getPreferences() {
  return await apiRequest("/preferences");
}

async function savePreferencesAPI(data) {
  return await apiRequest("/preferences", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(data),
  });
}

async function deletePreferencesAPI() {
  return await apiRequest("/preferences", {
    method: "DELETE",
  });
}

// ===============================
// Recommendations
// ===============================

async function getRecommendations() {
  return await apiRequest("/recommendations");
}

// ===============================
// AI
// ===============================

async function analyseJobAPI(id) {
  return await apiRequest(`/jobs/${id}/analyse`, {
    method: "POST",
  });
}

async function sendChatMessage(message) {
  return await apiRequest("/ai/chat", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      message,
    }),
  });
}

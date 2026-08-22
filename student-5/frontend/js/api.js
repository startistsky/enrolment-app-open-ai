const API_URL = "http://localhost:5005";

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
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
    throw new Error(data.error || `HTTP ${response.status}`);
  }

  return data;
}

// JOBS

async function getJobs(params = "") {
  return await apiRequest(`/jobs${params}`);
}

async function getJob(id) {
  return await apiRequest(`/jobs/${id}`);
}

async function createJob(data) {
  return await apiRequest("/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

async function updateJob(id, data) {
  return await apiRequest(`/jobs/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

async function deleteJob(id) {
  return await apiRequest(`/jobs/${id}`, {
    method: "DELETE",
  });
}

// SAVED

async function getSavedJobs() {
  return await apiRequest("/saved");
}

async function saveJobAPI(id) {
  return await apiRequest(`/saved/${id}`, {
    method: "POST",
  });
}

async function deleteSavedJob(id) {
  return await apiRequest(`/saved/${id}`, {
    method: "DELETE",
  });
}

// APPLICATIONS

async function getApplications() {
  return await apiRequest("/applications");
}

async function createApplication(jobId) {
  return await apiRequest("/applications", {
    method: "POST",

    body: JSON.stringify({
      job_id: jobId,
      status: "Applied",
    }),
  });
}

async function updateApplication(id, status, notes) {
  return await apiRequest(`/applications/${id}`, {
    method: "PUT",

    body: JSON.stringify({
      status,
      notes,
    }),
  });
}

async function deleteApplication(id) {
  return await apiRequest(`/applications/${id}`, {
    method: "DELETE",
  });
}

// PREFERENCES

async function getPreferences() {
  return await apiRequest("/preferences");
}

async function savePreferences(data) {
  return await apiRequest("/preferences", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

async function updatePreferences(data) {
  return await apiRequest("/preferences", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

async function deletePreferences() {
  return await apiRequest("/preferences", {
    method: "DELETE",
  });
}

// AI

async function analyseJobAPI(id) {
  return await apiRequest(`/jobs/${id}/analyse`, {
    method: "POST",
  });
}

async function getJobAnalysis(id) {
  return await apiRequest(`/jobs/${id}/analyse`);
}

async function sendChatMessage(message) {
  return await apiRequest("/ai/chat", {
    method: "POST",

    body: JSON.stringify({
      message,
    }),
  });
}

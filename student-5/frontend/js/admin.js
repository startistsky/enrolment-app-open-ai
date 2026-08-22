// =========================================================
// ADMIN JOB MANAGEMENT
// =========================================================

const jobForm = document.getElementById("job-form");

const jobsContainer = document.getElementById("admin-jobs");

const statusMessage = document.getElementById("admin-status");

let editingJobId = null;

// =========================================================
// Status
// =========================================================

function showStatus(message, type = "success") {
  if (!statusMessage) {
    return;
  }

  statusMessage.textContent = message;

  statusMessage.className = `status-message ${type}`;

  statusMessage.style.display = "block";
}

function clearStatus() {
  if (!statusMessage) {
    return;
  }

  statusMessage.textContent = "";

  statusMessage.className = "status-message";

  statusMessage.style.display = "none";
}

// =========================================================
// Get form data
// =========================================================

function getJobFormData() {
  return {
    title: document.getElementById("title").value.trim(),

    company: document.getElementById("company").value.trim(),

    location: document.getElementById("location").value.trim(),

    industry: document.getElementById("industry").value.trim(),

    job_type: document.getElementById("job-type").value.trim(),

    description: document.getElementById("description").value.trim(),

    requirements: document.getElementById("requirements").value.trim(),

    salary: document.getElementById("salary").value.trim(),

    application_url: document.getElementById("application-url").value.trim(),
  };
}

// =========================================================
// Create / Update
// =========================================================

async function saveAdminJob(event) {
  event.preventDefault();

  clearStatus();

  const job = getJobFormData();

  if (!job.title || !job.company) {
    showStatus("Job title and company are required.", "error");

    return;
  }

  try {
    if (editingJobId) {
      await updateJob(editingJobId, job);

      showStatus("Job updated successfully.", "success");
    } else {
      await createJob(job);

      showStatus("Job created successfully.", "success");
    }

    editingJobId = null;

    jobForm.reset();

    updateFormMode();

    await loadAdminJobs();
  } catch (error) {
    console.error(error);

    showStatus(error.message || "Could not save job.", "error");
  }
}

// =========================================================
// Load jobs
// =========================================================

async function loadAdminJobs() {
  try {
    const jobs = await getJobs();

    jobsContainer.innerHTML = "";

    if (!jobs.length) {
      jobsContainer.innerHTML = `
                <p>
                    No jobs available.
                </p>
                `;

      return;
    }

    jobs.forEach((job) => {
      jobsContainer.innerHTML += `

                    <div class="job-card">

                        <h3>
                            ${escapeHTML(job.title)}
                        </h3>

                        <p class="company">
                            ${escapeHTML(job.company)}
                        </p>

                        <p>
                            📍
                            ${escapeHTML(job.location || "Not specified")}
                        </p>

                        <p>
                            ${escapeHTML(job.industry || "No industry")}
                        </p>

                        <span class="tag">
                            ${escapeHTML(job.job_type || "Not specified")}
                        </span>

                        <p>
                            ${escapeHTML(job.description || "")}
                        </p>

                        <div
                            class="admin-actions"
                        >

                            <a
                                href="/job.html?id=${job.id}"
                            >
                                View
                            </a>

                            <button
                                type="button"
                                onclick="editJob(${job.id})"
                            >
                                Edit
                            </button>

                            <button
                                type="button"
                                class="danger-button"
                                onclick="removeJob(${job.id})"
                            >
                                Delete
                            </button>

                        </div>

                    </div>
                `;
    });
  } catch (error) {
    console.error(error);

    jobsContainer.innerHTML = `
            <p class="error">
                Could not load jobs:
                ${escapeHTML(error.message)}
            </p>
        `;
  }
}

// =========================================================
// Edit
// =========================================================

async function editJob(id) {
  clearStatus();

  try {
    const job = await getJob(id);

    editingJobId = id;

    document.getElementById("title").value = job.title || "";

    document.getElementById("company").value = job.company || "";

    document.getElementById("location").value = job.location || "";

    document.getElementById("industry").value = job.industry || "";

    document.getElementById("job-type").value = job.job_type || "";

    document.getElementById("description").value = job.description || "";

    document.getElementById("requirements").value = job.requirements || "";

    document.getElementById("salary").value = job.salary || "";

    document.getElementById("application-url").value =
      job.application_url || "";

    updateFormMode();

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });

    showStatus(`Editing "${job.title}".`, "success");
  } catch (error) {
    showStatus(error.message || "Could not load job.", "error");
  }
}

// =========================================================
// Delete
// =========================================================

async function removeJob(id) {
  clearStatus();

  try {
    await deleteJobAPI(id);

    showStatus("Job deleted successfully.", "success");

    await loadAdminJobs();
  } catch (error) {
    showStatus(error.message || "Could not delete job.", "error");
  }
}

// =========================================================
// Cancel edit
// =========================================================

function cancelEdit() {
  editingJobId = null;

  jobForm.reset();

  updateFormMode();

  clearStatus();
}

// =========================================================
// Form mode
// =========================================================

function updateFormMode() {
  const submitButton = document.getElementById("job-submit");

  const cancelButton = document.getElementById("cancel-edit");

  if (!submitButton) {
    return;
  }

  if (editingJobId) {
    submitButton.textContent = "Update Job";

    if (cancelButton) {
      cancelButton.style.display = "inline-block";
    }
  } else {
    submitButton.textContent = "Create Job";

    if (cancelButton) {
      cancelButton.style.display = "none";
    }
  }
}

// =========================================================
// Basic HTML escaping
// =========================================================

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// =========================================================
// Events
// =========================================================

if (jobForm) {
  jobForm.addEventListener("submit", saveAdminJob);
}

// =========================================================
// Start
// =========================================================

if (jobsContainer) {
  loadAdminJobs();
}

updateFormMode();

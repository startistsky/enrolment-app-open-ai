const jobForm = document.getElementById("job-form");

const jobsContainer = document.getElementById("admin-jobs");

const statusMessage = document.getElementById("job-message");

let editingJobId = null;

// Status
function showStatus(message, type = "success") {
    if (!statusMessage) {
        return;
    }

    statusMessage.textContent = message;

    statusMessage.className = `status-message ${type}`;
}

function clearStatus() {
    if (!statusMessage) {
        return;
    }

    statusMessage.textContent = "";

    statusMessage.className = "status-message";
}

// Form data
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

// Create update job
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
            await updateJobAPI(editingJobId, job);

            showStatus("Job updated successfully.", "success");
        } else {
            await createJobAPI(job);

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

// Load Jobs
async function loadAdminJobs() {
    if (!jobsContainer) {
        return;
    }

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

        <article class="job-card">


          <h3>

            ${escapeHtml(job.title)}

          </h3>


          <p class="company">

            ${escapeHtml(job.company)}

          </p>


          <p>

            📍

            ${escapeHtml(job.location || "Not specified")}

          </p>


          <p>

            ${escapeHtml(job.industry || "No industry")}

          </p>


          <span class="tag">

            ${escapeHtml(job.job_type || "Not specified")}

          </span>


          <p>

            ${escapeHtml(job.description || "")}

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


        </article>

      `;
        });
    } catch (error) {
        console.error(error);

        jobsContainer.innerHTML = `

      <p class="status-message error">

        Could not load jobs:

        ${escapeHtml(error.message)}

      </p>

    `;
    }
}

// Edit Job
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

        showStatus(`Editing "${job.title}".`, "info");
    } catch (error) {
        showStatus(error.message || "Could not load job.", "error");
    }
}

// Delete Job
async function removeJob(id) {
    const confirmed = confirm("Are you sure you want to delete this job?");

    if (!confirmed) {
        return;
    }

    clearStatus();

    try {
        await deleteJobAPI(id);

        showStatus("Job deleted successfully.", "success");

        await loadAdminJobs();
    } catch (error) {
        showStatus(error.message || "Could not delete job.", "error");
    }
}

// Cancel Edit
function cancelEdit() {
    editingJobId = null;

    if (jobForm) {
        jobForm.reset();
    }

    updateFormMode();

    clearStatus();
}

// Form Mode
function updateFormMode() {
    const submitButton = document.querySelector(
        "#job-form button[type='submit']",
    );

    const cancelButton = document.getElementById("cancel-edit");

    const formTitle = document.getElementById("form-title");

    if (editingJobId) {
        if (submitButton) {
            submitButton.textContent = "Update Job";
        }

        if (formTitle) {
            formTitle.textContent = "Edit Job";
        }

        if (cancelButton) {
            cancelButton.style.display = "inline-block";
        }
    } else {
        if (submitButton) {
            submitButton.textContent = "Save Job";
        }

        if (formTitle) {
            formTitle.textContent = "Add Job";
        }

        if (cancelButton) {
            cancelButton.style.display = "none";
        }
    }
}

// Events
if (jobForm) {
    jobForm.addEventListener("submit", saveAdminJob);
}

const cancelButton = document.getElementById("cancel-edit");

if (cancelButton) {
    cancelButton.addEventListener("click", cancelEdit);
}

// Start
document.addEventListener("DOMContentLoaded", () => {
    loadAdminJobs();

    updateFormMode();
});

const jobForm = document.getElementById("job-form");

const jobsContainer = document.getElementById("admin-jobs");

const adminMessage = document.getElementById("admin-message");

function showAdminMessage(text, type = "success") {
  adminMessage.className = `message ${type}`;

  adminMessage.textContent = text;
}

// ===============================
// Create
// ===============================

async function createJob(event) {
  event.preventDefault();

  const job = {
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

  if (!job.title || !job.company) {
    showAdminMessage("Job title and company are required.", "error");

    return;
  }

  try {
    await createJobAPI(job);

    showAdminMessage("Job created successfully.", "success");

    jobForm.reset();

    loadAdminJobs();
  } catch (error) {
    showAdminMessage(error.message, "error");
  }
}

// ===============================
// Load
// ===============================

async function loadAdminJobs() {
  try {
    const jobs = await getJobs();

    jobsContainer.innerHTML = "";

    if (jobs.length === 0) {
      jobsContainer.innerHTML = `<div class="empty-state">
                    No jobs available.
                </div>`;

      return;
    }

    jobs.forEach((job) => {
      jobsContainer.innerHTML += `

                <article class="job-card">

                    <h3>
                        ${job.title}
                    </h3>

                    <p class="company">
                        ${job.company}
                    </p>

                    <p>
                        📍 ${job.location}
                    </p>

                    <p>
                        ${job.industry}
                    </p>

                    <span class="tag">
                        ${job.job_type}
                    </span>

                    <p>
                        ${(job.description || "").substring(0, 120)}...
                    </p>

                    <div class="admin-actions">

                        <a
                            href="/job.html?id=${job.id}"
                        >
                            View
                        </a>

                        <button
                            class="danger-button"
                            onclick="deleteJob(${job.id})"
                        >
                            Delete
                        </button>

                    </div>

                </article>
            `;
    });
  } catch (error) {
    jobsContainer.innerHTML = `
            <div class="message error">
                ${error.message}
            </div>
        `;
  }
}

// ===============================
// Delete
// ===============================

async function deleteJob(id) {
  const message = document.getElementById("delete-message");

  message.className = "message";

  message.textContent = "Deleting job...";

  try {
    await deleteJobAPI(id);

    message.className = "message success";

    message.textContent = "Job deleted successfully.";

    loadAdminJobs();
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

if (jobForm) {
  jobForm.addEventListener("submit", createJob);
}

loadAdminJobs();

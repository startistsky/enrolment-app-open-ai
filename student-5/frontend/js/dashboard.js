// ============================================================
// Dashboard
// ============================================================

async function loadDashboard() {
  const savedContainer = document.getElementById("saved-jobs");

  const applicationContainer = document.getElementById("applications");

  try {
    const savedJobs = await getSavedJobs();

    const applications = await getApplications();

    // ====================================================
    // Saved jobs
    // ====================================================

    savedContainer.innerHTML = "";

    if (savedJobs.length === 0) {
      savedContainer.innerHTML = `
                <div class="empty-state">
                    <h3>
                        No saved jobs
                    </h3>

                    <p>
                        Save opportunities from the jobs page.
                    </p>
                </div>
            `;
    } else {
      savedJobs.forEach((job) => {
        savedContainer.innerHTML += `

                    <article class="job-card">

                        <span class="tag">
                            ${job.job_type || "Opportunity"}
                        </span>

                        <h3>
                            ${job.title}
                        </h3>

                        <p class="company">
                            ${job.company}
                        </p>

                        <p>
                            📍 ${job.location}
                        </p>

                        <a
                            href="/job.html?id=${job.id}"
                            class="view-link"
                        >
                            View Job →
                        </a>

                    </article>

                `;
      });
    }

    // ====================================================
    // Applications
    // ====================================================

    applicationContainer.innerHTML = "";

    if (applications.length === 0) {
      applicationContainer.innerHTML = `
                <div class="empty-state">

                    <h3>
                        No applications yet
                    </h3>

                    <p>
                        Apply to a job and it will appear here.
                    </p>

                </div>
            `;
    } else {
      applications.forEach((application) => {
        applicationContainer.innerHTML += `

                    <div
                        class="application"
                        id="application-${application.id}"
                    >

                        <div>

                            <h3>
                                ${application.title}
                            </h3>

                            <p class="company">
                                ${application.company}
                            </p>

                        </div>


                        <div class="application-controls">

                            <select
                                id="status-${application.id}"
                            >

                                <option
                                    ${
                                      application.status === "Applied"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Applied
                                </option>

                                <option
                                    ${
                                      application.status === "Interview"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Interview
                                </option>

                                <option
                                    ${
                                      application.status === "Offer"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Offer
                                </option>

                                <option
                                    ${
                                      application.status === "Rejected"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Rejected
                                </option>

                            </select>


                            <button
                                onclick="updateApplication(${application.id})"
                                class="secondary-button"
                            >
                                Update
                            </button>


                            <button
                                onclick="deleteApplication(${application.id})"
                                class="danger-button"
                            >
                                Delete
                            </button>

                        </div>


                        <p>
                            ${application.notes || ""}
                        </p>


                        <p
                            id="application-message-${application.id}"
                        ></p>

                    </div>

                `;
      });
    }
  } catch (error) {
    document.getElementById("dashboard-message").className = "message error";

    document.getElementById("dashboard-message").textContent =
      "Could not load dashboard: " + error.message;
  }
}

// ============================================================
// Update application
// ============================================================

async function updateApplication(id) {
  const status = document.getElementById(`status-${id}`).value;

  const message = document.getElementById(`application-message-${id}`);

  try {
    await updateApplicationAPI(id, status, "");

    message.className = "message success";

    message.textContent = "Application updated.";
  } catch (error) {
    message.className = "message error";

    message.textContent = "Update failed: " + error.message;
  }
}

// ============================================================
// Delete application
// ============================================================

async function deleteApplication(id) {
  const message = document.getElementById("dashboard-message");

  try {
    await deleteApplicationAPI(id);

    message.className = "message success";

    message.textContent = "Application deleted.";

    loadDashboard();
  } catch (error) {
    message.className = "message error";

    message.textContent = "Delete failed: " + error.message;
  }
}

loadDashboard();

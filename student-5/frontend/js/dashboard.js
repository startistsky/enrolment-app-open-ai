async function loadDashboard() {
  await loadSavedJobs();

  await loadApplications();
}

// ======================================
// Saved jobs
// ======================================

async function loadSavedJobs() {
  const container = document.getElementById("saved-jobs");

  try {
    const jobs = await getSavedJobs();

    container.innerHTML = "";

    if (!jobs.length) {
      container.innerHTML = `

                <p class="status-message">
                    You have no saved jobs.
                </p>

            `;

      return;
    }

    jobs.forEach((job) => {
      container.innerHTML += `

                <article class="job-card">

                    <span class="tag">
                        ${escapeHtml(job.job_type || "")}
                    </span>

                    <h3>
                        ${escapeHtml(job.title)}
                    </h3>

                    <p class="company">
                        ${escapeHtml(job.company)}
                    </p>

                    <p>
                        📍 ${escapeHtml(job.location || "")}
                    </p>

                    <div class="admin-actions">

                        <a
                            href="/job.html?id=${job.id}"
                        >
                            View
                        </a>

                        <button
                            class="danger-button"
                            onclick="removeSavedJob(${job.id})"
                        >
                            Remove
                        </button>

                    </div>

                </article>

            `;
    });
  } catch (error) {
    container.innerHTML = `

            <p class="status-message error">
                ${escapeHtml(error.message)}
            </p>

        `;
  }
}

async function removeSavedJob(id) {
  const message = document.getElementById("saved-message");

  try {
    await deleteSavedJobAPI(id);

    message.className = "status-message success";

    message.textContent = "Saved job removed.";

    await loadSavedJobs();
  } catch (error) {
    message.className = "status-message error";

    message.textContent = error.message;
  }
}

// ======================================
// Applications
// ======================================

async function loadApplications() {
  const container = document.getElementById("applications");

  try {
    const applications = await getApplications();

    container.innerHTML = "";

    if (!applications.length) {
      container.innerHTML = `

                <p class="status-message">
                    No applications yet.
                </p>

            `;

      return;
    }

    applications.forEach((application) => {
      container.innerHTML += `

                    <article class="application">

                        <div>

                            <h3>
                                ${escapeHtml(application.title)}
                            </h3>

                            <p>
                                ${escapeHtml(application.company)}
                            </p>

                            <p>
                                Applied:
                                ${escapeHtml(application.applied_at || "")}
                            </p>

                        </div>


                        <div class="application-controls">

                            <select
                                id="status-${application.id}"
                            >

                                <option
                                    ${
                                      application.status === "Interested"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Interested
                                </option>

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
                                class="secondary-button"
                                onclick="updateApplication(${application.id})"
                            >
                                Update
                            </button>


                            <button
                                class="danger-button"
                                onclick="deleteApplication(${application.id})"
                            >
                                Delete
                            </button>

                        </div>

                    </article>

                `;
    });
  } catch (error) {
    container.innerHTML = `

            <p class="status-message error">
                ${escapeHtml(error.message)}
            </p>

        `;
  }
}

async function updateApplication(id) {
  const status = document.getElementById(`status-${id}`).value;

  try {
    await updateApplicationAPI(
      id,

      {
        status,
        notes: "",
      },
    );

    await loadApplications();
  } catch (error) {
    console.error(error);
  }
}

async function deleteApplication(id) {
  try {
    await deleteApplicationAPI(id);

    await loadApplications();
  } catch (error) {
    console.error(error);
  }
}

// Escape
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadDashboard();

async function loadDashboard() {
  const savedContainer = document.getElementById("saved-jobs");

  const applicationContainer = document.getElementById("applications");

  const message = document.getElementById("dashboard-message");

  try {
    const savedJobs = await getSavedJobs();

    const applications = await getApplications();

    // =========================
    // Saved Jobs
    // =========================

    savedContainer.innerHTML = "";

    if (savedJobs.length === 0) {
      savedContainer.innerHTML = `<div class="empty-state">
                    No saved jobs yet.
                </div>`;
    } else {
      savedJobs.forEach((job) => {
        savedContainer.innerHTML += `

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

                        <a href="/job.html?id=${job.id}">
                            View Job →
                        </a>

                        <button
                            class="secondary-button"
                            onclick="removeSaved(${job.id})"
                        >
                            Remove
                        </button>

                    </article>
                `;
      });
    }

    // =========================
    // Applications
    // =========================

    applicationContainer.innerHTML = "";

    if (applications.length === 0) {
      applicationContainer.innerHTML = `<div class="empty-state">
                    No applications yet.
                </div>`;
    } else {
      applications.forEach((application) => {
        applicationContainer.innerHTML += `

                    <article class="application">

                        <h3>
                            ${application.title}
                        </h3>

                        <p>
                            ${application.company}
                        </p>

                        <label>Status</label>

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
                                  application.status === "Rejected"
                                    ? "selected"
                                    : ""
                                }
                            >
                                Rejected
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
                        </select>

                        <label>Notes</label>

                        <textarea
                            id="notes-${application.id}"
                        >${application.notes || ""}</textarea>

                        <div class="admin-actions">

                            <button
                                onclick="updateApplication(
                                    ${application.id}
                                )"
                            >
                                Save
                            </button>

                            <button
                                class="danger-button"
                                onclick="deleteApplication(
                                    ${application.id}
                                )"
                            >
                                Delete
                            </button>

                        </div>

                    </article>
                `;
      });
    }
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

async function removeSaved(id) {
  const message = document.getElementById("dashboard-message");

  try {
    await removeSavedJobAPI(id);

    message.className = "message success";

    message.textContent = "Saved job removed.";

    loadDashboard();
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

async function updateApplication(id) {
  const status = document.getElementById(`status-${id}`).value;

  const notes = document.getElementById(`notes-${id}`).value;

  const message = document.getElementById("dashboard-message");

  try {
    await updateApplicationAPI(id, status, notes);

    message.className = "message success";

    message.textContent = "Application updated.";
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

async function deleteApplication(id) {
  const message = document.getElementById("dashboard-message");

  try {
    await deleteApplicationAPI(id);

    message.className = "message success";

    message.textContent = "Application deleted.";

    loadDashboard();
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

loadDashboard();

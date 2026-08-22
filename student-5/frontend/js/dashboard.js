async function loadDashboard() {
  try {
    await loadSavedJobs();

    await loadApplications();
  } catch (error) {
    console.error(error);

    alert("Could not load dashboard.");
  }
}

// ========================================
// Saved Jobs
// ========================================

async function loadSavedJobs() {
  const container = document.getElementById("saved-jobs");

  const jobs = await getSavedJobs();

  container.innerHTML = "";

  if (!jobs.length) {
    container.innerHTML = `
            <div class="empty-state">
                You have no saved jobs.
            </div>
        `;

    return;
  }

  jobs.forEach((job) => {
    container.innerHTML += `

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

                <div class="card-actions">

                    <a href="/job.html?id=${job.id}">
                        View Job
                    </a>

                    <button
                        onclick="removeSavedJob(${job.id})"
                    >
                        Remove
                    </button>

                </div>

            </article>
        `;
  });
}

async function removeSavedJob(id) {
  if (!confirm("Remove this saved job?")) {
    return;
  }

  try {
    await deleteSavedJob(id);

    await loadSavedJobs();
  } catch (error) {
    alert(error.message);
  }
}

// ========================================
// Applications
// ========================================

async function loadApplications() {
  const container = document.getElementById("applications");

  const applications = await getApplications();

  container.innerHTML = "";

  if (!applications.length) {
    container.innerHTML = `
            <div class="empty-state">
                You have no applications yet.
            </div>
        `;

    return;
  }

  applications.forEach((application) => {
    container.innerHTML += `

                <div class="application">

                    <h3>
                        ${application.title}
                    </h3>

                    <p>
                        ${application.company}
                    </p>

                    <label>
                        Status
                    </label>

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
                              application.status === "Applied" ? "selected" : ""
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
                            ${application.status === "Offer" ? "selected" : ""}
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


                    <label>
                        Notes
                    </label>

                    <textarea
                        id="notes-${application.id}"
                    >${application.notes || ""}</textarea>


                    <div class="card-actions">

                        <button
                            onclick="updateApplicationFromPage(${application.id})"
                        >
                            Save Changes
                        </button>

                        <button
                            class="danger-button"
                            onclick="removeApplication(${application.id})"
                        >
                            Delete
                        </button>

                    </div>

                </div>
            `;
  });
}

async function updateApplicationFromPage(id) {
  const status = document.getElementById(`status-${id}`).value;

  const notes = document.getElementById(`notes-${id}`).value;

  try {
    await updateApplication(id, status, notes);

    alert("Application updated.");

    await loadApplications();
  } catch (error) {
    alert(error.message);
  }
}

async function removeApplication(id) {
  if (!confirm("Delete this application?")) {
    return;
  }

  try {
    await deleteApplication(id);

    await loadApplications();
  } catch (error) {
    alert(error.message);
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);

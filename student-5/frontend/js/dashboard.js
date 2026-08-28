async function loadDashboard() {
  await loadSavedJobs();

  await loadApplications();
}

// Saved Jobs
async function loadSavedJobs() {
  const container = document.getElementById("saved-jobs");

  if (!container) {
    return;
  }

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

            📍

            ${escapeHtml(job.location || "")}

          </p>


          <div class="admin-actions">

            <a
              href="/job.html?id=${job.id}"
            >
              View
            </a>


            <button
              type="button"
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
    console.error(error);

    container.innerHTML = `

      <p class="status-message error">

        ${escapeHtml(error.message)}

      </p>

    `;
  }
}

// Remove Saved Job
async function removeSavedJob(id) {
  const message = document.getElementById("saved-message");

  try {
    await deleteSavedJobAPI(id);

    if (message) {
      message.className = "status-message success";

      message.textContent = "Saved job removed.";
    }

    await loadSavedJobs();
  } catch (error) {
    if (message) {
      message.className = "status-message error";

      message.textContent = error.message;
    }
  }
}

// Applications
async function loadApplications() {
  const container = document.getElementById("applications");

  if (!container) {
    return;
  }

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


            <div
              class="application-controls"
            >

              <select
                id="status-${application.id}"
              >

                <option
                  value="Interested"
                  ${application.status === "Interested" ? "selected" : ""}
                >
                  Interested
                </option>


                <option
                  value="Applied"
                  ${application.status === "Applied" ? "selected" : ""}
                >
                  Applied
                </option>


                <option
                  value="Interview"
                  ${application.status === "Interview" ? "selected" : ""}
                >
                  Interview
                </option>


                <option
                  value="Offer"
                  ${application.status === "Offer" ? "selected" : ""}
                >
                  Offer
                </option>


                <option
                  value="Rejected"
                  ${application.status === "Rejected" ? "selected" : ""}
                >
                  Rejected
                </option>

              </select>


              <button
                type="button"
                class="secondary-button"
                onclick="updateApplication(${application.id})"
              >
                Update
              </button>


              <button
                type="button"
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
    console.error(error);

    container.innerHTML = `

      <p class="status-message error">

        ${escapeHtml(error.message)}

      </p>

    `;
  }
}

// Update Application
async function updateApplication(id) {
  const select = document.getElementById(`status-${id}`);

  if (!select) {
    return;
  }

  const status = select.value;

  try {
    await updateApplicationAPI(id, {
      status: status,
      notes: "",
    });

    await loadApplications();
  } catch (error) {
    console.error("Could not update application:", error);
  }
}

// Delete Application
async function deleteApplication(id) {
  try {
    await deleteApplicationAPI(id);

    await loadApplications();
  } catch (error) {
    console.error("Could not delete application:", error);
  }
}

// Start
document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
});

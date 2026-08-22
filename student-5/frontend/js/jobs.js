// ============================================================
// Jobs + Career Agent
// ============================================================

const jobContainer = document.getElementById("job-list");

const agentForm = document.getElementById("career-agent-form");

// ============================================================
// Search jobs
// ============================================================

async function searchJobs() {
  const search = document.getElementById("search").value.trim();

  const location = document.getElementById("location").value;

  const industry = document.getElementById("industry").value;

  const jobType = document.getElementById("job-type").value;

  const params = new URLSearchParams();

  if (search) {
    params.set("search", search);
  }

  if (location) {
    params.set("location", location);
  }

  if (industry) {
    params.set("industry", industry);
  }

  if (jobType) {
    params.set("job_type", jobType);
  }

  try {
    const jobs = await getJobs(`?${params.toString()}`);

    displayJobs(jobs);
  } catch (error) {
    jobContainer.innerHTML = `
            <div class="message error">
                Could not load jobs.
                ${error.message}
            </div>
        `;
  }
}

// ============================================================
// Display jobs
// ============================================================

function displayJobs(jobs) {
  jobContainer.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    jobContainer.innerHTML = `
            <div class="empty-state">

                <h3>
                    No opportunities found
                </h3>

                <p>
                    Try changing your search or career profile.
                </p>

            </div>
        `;

    return;
  }

  jobs.forEach((job) => {
    jobContainer.innerHTML += `

            <article class="job-card">

                <div class="job-card-top">

                    <span class="tag">
                        ${job.job_type || "Opportunity"}
                    </span>

                </div>


                <h3>
                    ${job.title}
                </h3>


                <p class="company">
                    ${job.company}
                </p>


                <p class="job-location">
                    📍 ${job.location || "Location not specified"}
                </p>


                <p class="job-industry">
                    ${job.industry || "Industry not specified"}
                </p>


                <p class="job-description">

                    ${(job.description || "").substring(0, 150)}

                    ...

                </p>


                <div class="job-card-footer">

                    <a
                        href="/job.html?id=${job.id}"
                        class="view-link"
                    >
                        View Details →
                    </a>

                </div>

            </article>

        `;
  });
}

// ============================================================
// Career Agent
// ============================================================

async function runCareerAgent(event) {
  event.preventDefault();

  const message = document.getElementById("agent-message");

  message.className = "message";

  message.textContent = "Career Agent is matching your profile...";

  const locations = document.getElementById("agent-locations").value.trim();

  const industries = document.getElementById("agent-industries").value.trim();

  const jobType = document.getElementById("agent-job-types").value;

  const skills = document.getElementById("agent-skills").value.trim();

  const goals = document.getElementById("agent-goals").value.trim();

  try {
    // Save profile first

    await savePreferencesAPI({
      locations,

      industries,

      job_types: jobType,

      skills,

      career_goals: goals,
    });

    // Build matching query

    const params = new URLSearchParams();

    if (locations) {
      const firstLocation = locations.split(",")[0].trim();

      params.set("location", firstLocation);
    }

    if (industries) {
      const firstIndustry = industries.split(",")[0].trim();

      params.set("industry", firstIndustry);
    }

    if (jobType) {
      params.set("job_type", jobType);
    }

    // Get matching jobs

    const jobs = await getJobs(`?${params.toString()}`);

    displayJobs(jobs);

    document.getElementById("recommendation-text").textContent =
      `The Career Agent found ${jobs.length} ` +
      `opportunities based on your profile.`;

    message.className = "message success";

    message.textContent = "Career profile saved and opportunities matched.";
  } catch (error) {
    message.className = "message error";

    message.textContent =
      "The Career Agent could not complete the request: " + error.message;
  }
}

// ============================================================
// Event listener
// ============================================================

if (agentForm) {
  agentForm.addEventListener("submit", runCareerAgent);
}

// ============================================================
// Initial jobs
// ============================================================

if (jobContainer) {
  searchJobs();
}

// ======================================
// Career Profile
// ======================================

const profileForm = document.getElementById("profile-form");

async function loadProfile() {
  try {
    const profile = await getCareerProfile();

    if (!profile || !profile.id) {
      return;
    }

    document.getElementById("locations").value = profile.locations || "";

    document.getElementById("industries").value = profile.industries || "";

    document.getElementById("job-types").value = profile.job_types || "";

    document.getElementById("education").value = profile.education || "";

    document.getElementById("skills").value = profile.skills || "";

    document.getElementById("experience").value = profile.experience || "";

    document.getElementById("career-goals").value = profile.career_goals || "";
  } catch (error) {
    console.error(error);
  }
}

profileForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const message = document.getElementById("profile-message");

  message.className = "status-message info";

  message.textContent = "Saving career profile...";

  const data = {
    locations: document.getElementById("locations").value,

    industries: document.getElementById("industries").value,

    job_types: document.getElementById("job-types").value,

    education: document.getElementById("education").value,

    skills: document.getElementById("skills").value,

    experience: document.getElementById("experience").value,

    career_goals: document.getElementById("career-goals").value,
  };

  try {
    await saveCareerProfileAPI(data);

    message.className = "status-message success";

    message.textContent = "Career profile saved successfully.";
  } catch (error) {
    message.className = "status-message error";

    message.textContent = error.message;
  }
});

// ======================================
// Search
// ======================================

async function searchJobs() {
  const search = document.getElementById("search").value;

  const location = document.getElementById("location").value;

  const industry = document.getElementById("industry").value;

  const jobType = document.getElementById("job-type").value;

  const params = new URLSearchParams();

  if (search) params.set("search", search);

  if (location) params.set("location", location);

  if (industry) params.set("industry", industry);

  if (jobType) params.set("job_type", jobType);

  try {
    const jobs = await getJobs(`?${params.toString()}`);

    displayJobs(jobs);
  } catch (error) {
    document.getElementById("job-list").innerHTML = `

            <p class="status-message error">
                Could not load jobs:
                ${escapeHtml(error.message)}
            </p>

        `;
  }
}

// ======================================
// Display jobs
// ======================================

function displayJobs(jobs) {
  const container = document.getElementById("job-list");

  container.innerHTML = "";

  if (!jobs.length) {
    container.innerHTML = `

            <p class="status-message">
                No jobs found.
            </p>

        `;

    return;
  }

  jobs.forEach((job) => {
    container.innerHTML += `

            <article class="job-card">

                <span class="tag">
                    ${escapeHtml(job.job_type || "Opportunity")}
                </span>

                <h3>
                    ${escapeHtml(job.title)}
                </h3>

                <p class="company">
                    ${escapeHtml(job.company)}
                </p>

                <p class="job-location">
                    📍 ${escapeHtml(job.location || "Not specified")}
                </p>

                <p class="job-industry">
                    ${escapeHtml(job.industry || "")}
                </p>

                <p class="job-description">
                    ${escapeHtml((job.description || "").substring(0, 160))}...
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

// ======================================
// Agent
// ======================================

async function runAgent() {
  const button = document.getElementById("agent-button");

  const status = document.getElementById("agent-status");

  const results = document.getElementById("agent-results");

  button.disabled = true;

  button.textContent = "Agent working...";

  status.className = "status-message info";

  status.textContent = "Analysing your profile and available opportunities...";

  results.innerHTML = "";

  try {
    const result = await runCareerAgentAPI();

    if (!result.success) {
      throw new Error(result.message);
    }

    status.className = "status-message success";

    status.textContent = result.message;

    if (!result.recommendations || !result.recommendations.length) {
      results.innerHTML = `

                <div class="agent-empty">

                    No strong matches were found.

                    Try adding more skills,
                    education or career goals
                    to your profile.

                </div>

            `;

      return;
    }

    result.recommendations.forEach((recommendation) => {
      loadRecommendation(recommendation);
    });
  } catch (error) {
    status.className = "status-message error";

    status.textContent =
      "The Career Agent could not complete the request: " + error.message;
  } finally {
    button.disabled = false;

    button.textContent = "Find My Opportunities";
  }
}

async function loadRecommendation(recommendation) {
  try {
    const job = await getJob(recommendation.job_id);

    const results = document.getElementById("agent-results");

    results.innerHTML += `

            <article class="job-card">

                <span class="match-score">
                    ${recommendation.score}% Match
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

                <p class="job-description">
                    ${escapeHtml(recommendation.reason)}
                </p>

                <div class="job-card-footer">

                    <a
                        href="/job.html?id=${job.id}"
                        class="view-link"
                    >
                        View Opportunity →
                    </a>

                </div>

            </article>

        `;
  } catch (error) {
    console.error(error);
  }
}

// ======================================
// Escape HTML
// ======================================

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Start
loadProfile();
searchJobs();

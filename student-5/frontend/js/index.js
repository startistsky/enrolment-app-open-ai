async function searchJobs() {
  const searchInput = document.getElementById("search");

  const locationInput = document.getElementById("location");

  const industryInput = document.getElementById("industry");

  const jobTypeInput = document.getElementById("job-type");

  const search = searchInput ? searchInput.value.trim() : "";

  const location = locationInput ? locationInput.value.trim() : "";

  const industry = industryInput ? industryInput.value.trim() : "";

  const jobType = jobTypeInput ? jobTypeInput.value.trim() : "";

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
    const query = params.toString();

    const jobs = await getJobs(query ? `?${query}` : "");

    displayJobs(jobs);
  } catch (error) {
    console.error("Could not load jobs:", error);

    const container = document.getElementById("job-list");

    if (container) {
      container.innerHTML = `

        <p class="status-message error">

          Could not load jobs:

          ${escapeHtml(error.message)}

        </p>

      `;
    }
  }
}

// Display Jobs
function displayJobs(jobs) {
  const container = document.getElementById("job-list");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (!jobs || !jobs.length) {
    container.innerHTML = `

      <p class="status-message">
        No jobs found.
      </p>

    `;

    return;
  }

  jobs.forEach((job) => {
    const description = job.description || "";

    const shortDescription =
      description.length > 160
        ? description.substring(0, 160) + "..."
        : description;

    container.innerHTML += `

      <article class="job-card">

        <span class="tag">

          ${escapeHtml(job.job_type || "Opportunity")}

        </span>


        <h3>

          ${escapeHtml(job.title || "Untitled Job")}

        </h3>


        <p class="company">

          ${escapeHtml(job.company || "Company not specified")}

        </p>


        <p class="job-location">

          📍

          ${escapeHtml(job.location || "Not specified")}

        </p>


        <p class="job-industry">

          ${escapeHtml(job.industry || "")}

        </p>


        <p class="job-description">

          ${escapeHtml(shortDescription)}

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

// Start
document.addEventListener("DOMContentLoaded", () => {
  searchJobs();
});

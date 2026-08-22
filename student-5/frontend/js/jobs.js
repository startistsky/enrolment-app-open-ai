async function searchJobs() {
  const search = document.getElementById("search").value.trim();

  const location = document.getElementById("location").value;

  const industry = document.getElementById("industry").value;

  const jobType = document.getElementById("job-type").value;

  const params = new URLSearchParams();

  if (search) params.set("search", search);

  if (location) params.set("location", location);

  if (industry) params.set("industry", industry);

  if (jobType) params.set("job_type", jobType);

  try {
    const jobs = await getJobs(params.toString() ? `?${params}` : "");

    displayJobs(jobs);
  } catch (error) {
    console.error(error);

    document.getElementById("job-list").innerHTML = `
            <p>
                Could not load jobs.
                Make sure Flask is running
                on port 5005.
            </p>
        `;
  }
}

function displayJobs(jobs) {
  const container = document.getElementById("job-list");

  container.innerHTML = "";

  if (!jobs.length) {
    container.innerHTML = `
            <div class="empty-state">
                No jobs found.
            </div>
        `;

    return;
  }

  jobs.forEach((job) => {
    const description = job.description || "";

    container.innerHTML += `

            <article class="job-card">

                <h3>
                    ${job.title}
                </h3>

                <p class="company">
                    ${job.company}
                </p>

                <p>
                    📍 ${job.location || "Not specified"}
                </p>

                <p>
                    ${job.industry || "General"}
                </p>

                <span class="tag">
                    ${job.job_type || "Opportunity"}
                </span>

                <p>
                    ${description.substring(0, 150)}
                    ${description.length > 150 ? "..." : ""}
                </p>

                <a href="/job.html?id=${job.id}">
                    View Details →
                </a>

            </article>
        `;
  });
}

document.addEventListener("DOMContentLoaded", searchJobs);

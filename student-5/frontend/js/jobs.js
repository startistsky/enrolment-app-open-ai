async function searchJobs() {
  const search = document.getElementById("search").value;

  const location = document.getElementById("location").value;

  const industry = document.getElementById("industry").value;

  const jobType = document.getElementById("job-type").value;

  let params = "?";

  params += `search=${encodeURIComponent(search)}`;

  params += `&location=${encodeURIComponent(location)}`;

  params += `&industry=${encodeURIComponent(industry)}`;

  params += `&job_type=${encodeURIComponent(jobType)}`;

  const message = document.getElementById("jobs-message");

  try {
    const jobs = await getJobs(params);

    displayJobs(jobs);

    message.className = "message";

    message.textContent = `${jobs.length} opportunity(s) found.`;
  } catch (error) {
    message.className = "message error";

    message.textContent = error.message;
  }
}

function displayJobs(jobs) {
  const container = document.getElementById("job-list");

  container.innerHTML = "";

  if (jobs.length === 0) {
    container.innerHTML = `<div class="empty-state">
                No jobs found.
            </div>`;

    return;
  }

  jobs.forEach((job) => {
    container.innerHTML += `

            <article class="job-card">

                <h3>${job.title}</h3>

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
                    ${job.job_type || "Not specified"}
                </span>

                <p>
                    ${(job.description || "").substring(0, 150)}...
                </p>

                <a href="/job.html?id=${job.id}">
                    View Details →
                </a>

            </article>
        `;
  });
}

searchJobs();

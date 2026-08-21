async function searchJobs() {

    const search =
        document.getElementById("search").value;

    const location =
        document.getElementById("location").value;

    const industry =
        document.getElementById("industry").value;

    const jobType =
        document.getElementById("job-type").value;


    let params = "?";

    params += `search=${encodeURIComponent(search)}`;
    params += `&location=${encodeURIComponent(location)}`;
    params += `&industry=${encodeURIComponent(industry)}`;
    params += `&job_type=${encodeURIComponent(jobType)}`;


    const jobs = await getJobs(params);

    displayJobs(jobs);
}


function displayJobs(jobs) {

    const container =
        document.getElementById("job-list");

    container.innerHTML = "";


    if (jobs.length === 0) {

        container.innerHTML =
            "<p>No jobs found.</p>";

        return;
    }


    jobs.forEach(job => {

        container.innerHTML += `

            <div class="job-card">

                <h3>${job.title}</h3>

                <p class="company">
                    ${job.company}
                </p>

                <p>
                    📍 ${job.location}
                </p>

                <p>
                    ${job.industry}
                </p>

                <span class="tag">
                    ${job.job_type}
                </span>

                <p>
                    ${job.description.substring(0, 150)}...
                </p>

                <a href="job.html?id=${job.id}">
                    View Details
                </a>

            </div>

        `;
    });
}


// Load jobs when page opens

searchJobs();
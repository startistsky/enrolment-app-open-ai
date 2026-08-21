async function loadDashboard() {

    const savedJobs =
        await getSavedJobs();

    const applications =
        await getApplications();


    // Saved jobs

    const savedContainer =
        document.getElementById("saved-jobs");

    savedContainer.innerHTML = "";


    savedJobs.forEach(job => {

        savedContainer.innerHTML += `

            <div class="job-card">

                <h3>${job.title}</h3>

                <p>${job.company}</p>

                <p>${job.location}</p>

                <a href="job.html?id=${job.id}">
                    View Job
                </a>

            </div>

        `;
    });


    // Applications

    const applicationContainer =
        document.getElementById("applications");

    applicationContainer.innerHTML = "";


    applications.forEach(application => {

        applicationContainer.innerHTML += `

            <div class="application">

                <h3>
                    ${application.title}
                </h3>

                <p>
                    ${application.company}
                </p>

                <strong>
                    Status: ${application.status}
                </strong>

                <p>
                    ${application.notes || ""}
                </p>

            </div>

        `;
    });
}


loadDashboard();
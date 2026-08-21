const params =
    new URLSearchParams(window.location.search);

const jobId = params.get("id");


async function loadJob() {

    const job = await getJob(jobId);

    const container =
        document.getElementById("job-details");


    container.innerHTML = `

        <h1>${job.title}</h1>

        <h2>${job.company}</h2>

        <p>📍 ${job.location}</p>

        <p>
            <strong>Industry:</strong>
            ${job.industry}
        </p>

        <p>
            <strong>Type:</strong>
            ${job.job_type}
        </p>

        <p>
            <strong>Salary:</strong>
            ${job.salary || "Not specified"}
        </p>


        <h2>Job Description</h2>

        <p>
            ${job.description}
        </p>


        <h2>Requirements</h2>

        <p>
            ${job.requirements}
        </p>

    `;
}


async function saveJob() {

    await saveJobAPI(jobId);

    alert("Job saved!");
}


async function applyJob() {

    await createApplication(jobId);

    alert("Application added to your dashboard!");
}


async function analyseJob() {

    const result =
        await analyseJobAPI(jobId);

    document.getElementById(
        "ai-analysis"
    ).innerHTML = `

        <h3>Skills</h3>
        <p>${result.skills}</p>

        <h3>Qualifications</h3>
        <p>${result.qualifications}</p>

        <h3>Experience</h3>
        <p>${result.experience}</p>

        <h3>ATS Keywords</h3>
        <p>${result.ats_keywords}</p>

        <h3>Summary</h3>
        <p>${result.summary}</p>

    `;
}


async function sendMessage() {

    const input =
        document.getElementById("chat-input");

    const message = input.value;

    if (!message) return;


    const result =
        await sendChatMessage(message);


    const chat =
        document.getElementById("chat-messages");


    chat.innerHTML += `

        <div class="user-message">
            ${message}
        </div>

        <div class="ai-message">
            ${result.response}
        </div>

    `;


    input.value = "";
}


loadJob();
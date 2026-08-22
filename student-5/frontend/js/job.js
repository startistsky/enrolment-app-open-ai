const params =
    new URLSearchParams(
        window.location.search
    );

const jobId =
    params.get("id");


async function loadJob() {

    const container =
        document.getElementById("job-details");

    try {

        const job =
            await getJob(jobId);

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

    } catch (error) {

        container.innerHTML = `
            <div class="message error">
                ${error.message}
            </div>
        `;
    }
}


async function saveJob() {

    const message =
        document.getElementById("job-message");

    try {

        await saveJobAPI(jobId);

        message.className =
            "message success";

        message.textContent =
            "Job saved successfully.";

    } catch (error) {

        message.className =
            "message error";

        message.textContent =
            error.message;
    }
}


async function applyJob() {

    const message =
        document.getElementById("job-message");

    try {

        await createApplication(jobId);

        message.className =
            "message success";

        message.textContent =
            "Application added to your dashboard.";

    } catch (error) {

        message.className =
            "message error";

        message.textContent =
            error.message;
    }
}


async function analyseJob() {

    const container =
        document.getElementById("ai-analysis");

    container.innerHTML =
        `<p>Analysing this job...</p>`;

    try {

        const result =
            await analyseJobAPI(jobId);

        container.innerHTML = `

            <div class="ai-message">

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

            </div>
        `;

    } catch (error) {

        container.innerHTML = `
            <div class="message error">
                ${error.message}
            </div>
        `;
    }
}


async function sendMessage() {

    const input =
        document.getElementById("chat-input");

    const message =
        input.value.trim();

    if (!message) {
        return;
    }

    const chat =
        document.getElementById("chat-messages");

    chat.innerHTML += `

        <div class="user-message">
            ${message}
        </div>
    `;

    input.value = "";

    try {

        const result =
            await sendChatMessage(message);

        chat.innerHTML += `

            <div class="ai-message">
                ${result.response}
            </div>
        `;

    } catch (error) {

        chat.innerHTML += `

            <div class="message error">
                ${error.message}
            </div>
        `;
    }
}


loadJob();
// ============================================================
// Job Details
// ============================================================

const params =
    new URLSearchParams(
        window.location.search
    );

const jobId =
    params.get("id");


// ============================================================
// Load job
// ============================================================

async function loadJob() {

    const container =
        document.getElementById(
            "job-details"
        );


    if (!jobId) {

        container.innerHTML = `
            <div class="message error">
                No job was selected.
            </div>
        `;

        return;
    }


    try {

        const job =
            await getJob(jobId);


        container.innerHTML = `

            <div class="job-detail-card">

                <span class="tag">
                    ${job.job_type || "Opportunity"}
                </span>


                <h1>
                    ${job.title}
                </h1>


                <h2>
                    ${job.company}
                </h2>


                <p class="job-location">
                    📍 ${job.location || "Not specified"}
                </p>


                <p>
                    <strong>Industry:</strong>
                    ${job.industry || "Not specified"}
                </p>


                <p>
                    <strong>Salary:</strong>
                    ${job.salary || "Not specified"}
                </p>


                <hr>


                <h2>
                    Job Description
                </h2>

                <p class="long-text">
                    ${job.description || "No description provided."}
                </p>


                <h2>
                    Requirements
                </h2>

                <p class="long-text">
                    ${job.requirements || "No requirements provided."}
                </p>


                ${
                    job.application_url
                    ? `
                        <a
                            class="primary-button inline-button"
                            href="${job.application_url}"
                            target="_blank"
                        >
                            External Application →
                        </a>
                    `
                    : ""
                }

            </div>

        `;

    } catch (error) {

        container.innerHTML = `
            <div class="message error">
                Could not load this job.
                ${error.message}
            </div>
        `;
    }
}


// ============================================================
// Save
// ============================================================

async function saveJob() {

    const message =
        document.getElementById(
            "job-action-message"
        );


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
            "Could not save job: "
            + error.message;
    }
}


// ============================================================
// Apply
// ============================================================

async function applyJob() {

    const message =
        document.getElementById(
            "job-action-message"
        );


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
            "Could not create application: "
            + error.message;
    }
}


// ============================================================
// AI analysis
// ============================================================

async function analyseJob() {

    const container =
        document.getElementById(
            "ai-analysis"
        );


    container.innerHTML = `
        <div class="message">
            AI is analysing this opportunity...
        </div>
    `;


    try {

        const result =
            await analyseJobAPI(jobId);


        container.innerHTML = `

            <div class="analysis-result">

                <h3>
                    Skills
                </h3>

                <p>
                    ${result.skills || "Not available"}
                </p>


                <h3>
                    Qualifications
                </h3>

                <p>
                    ${result.qualifications || "Not available"}
                </p>


                <h3>
                    Experience
                </h3>

                <p>
                    ${result.experience || "Not available"}
                </p>


                <h3>
                    ATS Keywords
                </h3>

                <p>
                    ${result.ats_keywords || "Not available"}
                </p>


                <h3>
                    Summary
                </h3>

                <p>
                    ${result.summary || "Not available"}
                </p>

            </div>

        `;

    } catch (error) {

        container.innerHTML = `
            <div class="message error">
                AI analysis failed:
                ${error.message}
            </div>
        `;
    }
}


// ============================================================
// Chat
// ============================================================

async function sendMessage() {

    const input =
        document.getElementById(
            "chat-input"
        );


    const message =
        input.value.trim();


    if (!message) {
        return;
    }


    const chat =
        document.getElementById(
            "chat-messages"
        );


    const status =
        document.getElementById(
            "chat-message"
        );


    chat.innerHTML += `

        <div class="user-message">

            ${message}

        </div>

    `;


    input.value = "";


    status.className =
        "message";

    status.textContent =
        "Career Agent is thinking...";


    try {

        const result =
            await sendChatMessage(
                message
            );


        chat.innerHTML += `

            <div class="ai-message">

                ${result.response}

            </div>

        `;


        status.textContent = "";


    } catch (error) {

        status.className =
            "message error";

        status.textContent =
            "AI assistant failed: "
            + error.message;
    }
}


loadJob();
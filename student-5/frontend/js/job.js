const params = new URLSearchParams(window.location.search);
const jobId = params.get("id");

let currentJob = null;
let analysing = false;

function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// Keep compatibility with existing code
function escapeHtml(value) {
    return escapeHTML(value);
}


// ============================================================
// Simple AI analysis
// ============================================================

function displayAnalysis(value) {
    if (!value) {
        return "<p>No information available.</p>";
    }

    if (Array.isArray(value)) {
        return `
            <ul>
                ${value.map(item => `
                    <li>${escapeHTML(item)}</li>
                `).join("")}
            </ul>
        `;
    }

    return `
        <p>
            ${escapeHTML(value)}
        </p>
    `;
}


// ============================================================
// Render AI analysis
// ============================================================

function renderAIAnalysis(result) {

    const container = document.getElementById("ai-analysis");

    if (!container) {
        return;
    }

    container.innerHTML = `

        <div class="analysis-grid">

            <div class="analysis-card">
                <h3>Skills</h3>

                ${displayAnalysis(result.skills)}
            </div>


            <div class="analysis-card">
                <h3>Qualifications</h3>

                ${displayAnalysis(result.qualifications)}
            </div>


            <div class="analysis-card">
                <h3>Experience</h3>

                ${displayAnalysis(result.experience)}
            </div>


            <div class="analysis-card">
                <h3>ATS Keywords</h3>

                ${displayAnalysis(result.ats_keywords)}
            </div>


            <div class="analysis-card analysis-summary">
                <h3>Summary</h3>

                ${displayAnalysis(result.summary)}
            </div>

        </div>

    `;
}


// ============================================================
// Load job
// ============================================================

async function loadJob() {

    const container = document.getElementById("job-details");

    if (!container) {
        return;
    }

    if (!jobId) {

        container.innerHTML = `
            <p class="status-message error">
                No job selected.
            </p>
        `;

        return;
    }

    try {

        currentJob = await getJob(jobId);

        if (!currentJob) {
            throw new Error("Job not found.");
        }

        container.innerHTML = `

            <article class="job-detail-card">

                <span class="tag">
                    ${escapeHTML(
                        currentJob.job_type || "Opportunity"
                    )}
                </span>


                <h1>
                    ${escapeHTML(
                        currentJob.title || "Untitled Job"
                    )}
                </h1>


                <h2>
                    ${escapeHTML(
                        currentJob.company || "Company not specified"
                    )}
                </h2>


                <p>
                    📍 ${escapeHTML(
                        currentJob.location || "Location not specified"
                    )}
                </p>


                <p>
                    <strong>Industry:</strong>
                    ${escapeHTML(
                        currentJob.industry || "Not specified"
                    )}
                </p>


                <p>
                    <strong>Salary:</strong>
                    ${escapeHTML(
                        currentJob.salary || "Not specified"
                    )}
                </p>


                <hr>


                <h2>
                    Job Description
                </h2>

                <p class="long-text">
                    ${escapeHTML(
                        currentJob.description ||
                        "No job description available."
                    )}
                </p>


                <h2>
                    Requirements
                </h2>

                <p class="long-text">
                    ${escapeHTML(
                        currentJob.requirements ||
                        "No requirements provided."
                    )}
                </p>


                ${
                    currentJob.application_url
                        ? `
                            <div class="job-external-link">

                                <a
                                    href="${escapeHTML(
                                        currentJob.application_url
                                    )}"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="primary-button"
                                >
                                    Open Application
                                </a>

                            </div>
                        `
                        : ""
                }

            </article>

        `;

    } catch (error) {

        console.error(
            "Could not load job:",
            error
        );

        container.innerHTML = `

            <p class="status-message error">

                Could not load job:

                ${escapeHTML(error.message)}

            </p>

        `;
    }
}


// ============================================================
// Save job
// ============================================================

async function saveJob() {

    const message =
        document.getElementById("job-action-message");

    if (!jobId || !message) {
        return;
    }

    try {

        message.className =
            "status-message info";

        message.textContent =
            "Saving job...";

        await saveJobAPI(jobId);

        message.className =
            "status-message success";

        message.textContent =
            "Job saved successfully.";

    } catch (error) {

        console.error(
            "Save job error:",
            error
        );

        message.className =
            "status-message error";

        message.textContent =
            `Could not save job: ${error.message}`;
    }
}


// ============================================================
// Apply
// ============================================================

async function applyJob() {

    const message =
        document.getElementById("job-action-message");

    if (!jobId || !message) {
        return;
    }

    try {

        message.className =
            "status-message info";

        message.textContent =
            "Adding application...";

        await createApplication(jobId);

        message.className =
            "status-message success";

        message.textContent =
            "Application added successfully.";

    } catch (error) {

        console.error(
            "Application error:",
            error
        );

        message.className =
            "status-message error";

        message.textContent =
            `Could not create application: ${error.message}`;
    }
}


// ============================================================
// AI / ATS Analysis
// ============================================================

async function analyseJob() {

    const container =
        document.getElementById("ai-analysis");

    if (!container || !jobId) {
        return;
    }

    if (analysing) {
        return;
    }

    analysing = true;

    container.innerHTML = `

        <p class="status-message info">
            Analysing job...
        </p>

    `;

    try {

        const result =
            await analyseJobAPI(jobId);

        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.error ||
                "Analysis failed."
            );
        }

        renderAIAnalysis(result);

    } catch (error) {

        console.error(
            "AI analysis error:",
            error
        );

        container.innerHTML = `

            <p class="status-message error">

                AI analysis failed:

                ${escapeHTML(error.message)}

            </p>

        `;

    } finally {

        analysing = false;

    }
}


// ============================================================
// Chat
// ============================================================

async function sendMessage() {

    const input =
        document.getElementById("chat-input");

    const chat =
        document.getElementById("chat-messages");

    const status =
        document.getElementById("chat-message");

    if (
        !input ||
        !chat ||
        !status ||
        !jobId
    ) {
        return;
    }

    const message =
        input.value.trim();

    if (!message) {
        return;
    }


    // User message

    chat.innerHTML += `

        <div class="user-message">
            ${escapeHTML(message)}
        </div>

    `;

    input.value = "";


    status.className =
        "status-message info";

    status.textContent =
        "Career Agent is thinking...";


    try {

        const result =
            await sendChatMessage(
                message,
                jobId
            );

        const response =
            result.response ||
            "No response received.";


        chat.innerHTML += `

            <div class="ai-message">

                ${escapeHTML(response)}

            </div>

        `;


        status.className =
            "status-message";

        status.textContent = "";


        chat.scrollTop =
            chat.scrollHeight;

    } catch (error) {

        console.error(
            "Career Agent chat error:",
            error
        );

        status.className =
            "status-message error";

        status.textContent =
            `Career Agent could not complete the request: ${error.message}`;
    }
}


// ============================================================
// Enter to send chat
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const input =
            document.getElementById("chat-input");

        if (!input) {
            return;
        }

        input.addEventListener(
            "keydown",
            event => {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    sendMessage();
                }

            }
        );

    }
);

loadJob();
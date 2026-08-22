const params = new URLSearchParams(window.location.search);

const jobId = params.get("id");

async function loadJob() {
  const container = document.getElementById("job-details");

  if (!jobId) {
    container.innerHTML = `
            <p>
                No job selected.
            </p>
        `;

    return;
  }

  try {
    const job = await getJob(jobId);

    container.innerHTML = `

            <h1>
                ${job.title}
            </h1>

            <h2>
                ${job.company}
            </h2>

            <p>
                📍 ${job.location || "Not specified"}
            </p>

            <p>
                <strong>Industry:</strong>
                ${job.industry || "Not specified"}
            </p>

            <p>
                <strong>Type:</strong>
                ${job.job_type || "Not specified"}
            </p>

            <p>
                <strong>Salary:</strong>
                ${job.salary || "Not specified"}
            </p>

            <h2>
                Job Description
            </h2>

            <p>
                ${job.description || "No description provided."}
            </p>

            <h2>
                Requirements
            </h2>

            <p>
                ${job.requirements || "No requirements provided."}
            </p>

            ${
              job.application_url
                ? `
                    <a
                        class="external-link"
                        href="${job.application_url}"
                        target="_blank"
                    >
                        Apply on company website →
                    </a>
                `
                : ""
            }

        `;
  } catch (error) {
    console.error(error);

    container.innerHTML = `
            <p>
                Could not load this job.
            </p>
        `;
  }
}

async function saveJob() {
  try {
    await saveJobAPI(jobId);

    alert("Job saved!");
  } catch (error) {
    alert(error.message);
  }
}

async function applyJob() {
  try {
    await createApplication(jobId);

    alert("Application added to your dashboard!");
  } catch (error) {
    alert(error.message);
  }
}

async function analyseJob() {
  const container = document.getElementById("ai-analysis");

  container.innerHTML = `
        <p>
            Analysing this job...
        </p>
    `;

  try {
    const result = await analyseJobAPI(jobId);

    container.innerHTML = `

            <div class="ai-result">

                <h3>
                    Skills
                </h3>

                <p>
                    ${result.skills}
                </p>


                <h3>
                    Qualifications
                </h3>

                <p>
                    ${result.qualifications}
                </p>


                <h3>
                    Experience
                </h3>

                <p>
                    ${result.experience}
                </p>


                <h3>
                    ATS Keywords
                </h3>

                <p>
                    ${result.ats_keywords}
                </p>


                <h3>
                    Summary
                </h3>

                <p>
                    ${result.summary}
                </p>

            </div>

        `;
  } catch (error) {
    container.innerHTML = `
            <p>
                AI analysis failed:
                ${error.message}
            </p>
        `;
  }
}

async function sendMessage() {
  const input = document.getElementById("chat-input");

  const message = input.value.trim();

  if (!message) return;

  const chat = document.getElementById("chat-messages");

  chat.innerHTML += `

        <div class="user-message">
            ${message}
        </div>

    `;

  input.value = "";

  try {
    const result = await sendChatMessage(message);

    chat.innerHTML += `

            <div class="ai-message">
                ${result.response}
            </div>

        `;

    chat.scrollTop = chat.scrollHeight;
  } catch (error) {
    chat.innerHTML += `

            <div class="ai-message">
                Sorry, I couldn't respond.
            </div>

        `;
  }
}

document.addEventListener("DOMContentLoaded", loadJob);

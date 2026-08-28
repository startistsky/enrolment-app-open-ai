const params = new URLSearchParams(window.location.search);

const jobId = params.get("id");

let currentJob = null;

let analysing = false;

// Display analysis value
function displayAnalysis(value) {
  if (!value) {
    return `
      <p>
        No information available.
      </p>
    `;
  }

  if (Array.isArray(value)) {
    return `
      <ul>
        ${value
          .map(
            (item) => `
              <li>
                ${escapeHtml(item)}
              </li>
            `,
          )
          .join("")}
      </ul>
    `;
  }

  return `
    <p>
      ${escapeHtml(value)}
    </p>
  `;
}

// Render AI analysis
function renderAIAnalysis(result) {
  const container = document.getElementById("ai-analysis");

  if (!container) {
    return;
  }

  container.innerHTML = `

    <div class="analysis-grid">

      <div class="analysis-card">

        <h3>
          Skills
        </h3>

        ${displayAnalysis(result.skills)}

      </div>


      <div class="analysis-card">

        <h3>
          Qualifications
        </h3>

        ${displayAnalysis(result.qualifications)}

      </div>


      <div class="analysis-card">

        <h3>
          Experience
        </h3>

        ${displayAnalysis(result.experience)}

      </div>


      <div class="analysis-card">

        <h3>
          ATS Keywords
        </h3>

        ${displayAnalysis(result.ats_keywords)}

      </div>


      <div
        class="analysis-card analysis-summary"
      >

        <h3>
          Summary
        </h3>

        ${displayAnalysis(result.summary)}

      </div>

    </div>

  `;
}

// Load job
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

      <article
        class="job-detail-card"
      >

        <span class="tag">

          ${escapeHtml(currentJob.job_type || "Opportunity")}

        </span>


        <h1>

          ${escapeHtml(currentJob.title || "Untitled Job")}

        </h1>


        <h2>

          ${escapeHtml(currentJob.company || "Company not specified")}

        </h2>


        <p>

          📍

          ${escapeHtml(currentJob.location || "Location not specified")}

        </p>


        <p>

          <strong>
            Industry:
          </strong>

          ${escapeHtml(currentJob.industry || "Not specified")}

        </p>


        <p>

          <strong>
            Job Type:
          </strong>

          ${escapeHtml(currentJob.job_type || "Not specified")}

        </p>


        <p>

          <strong>
            Salary:
          </strong>

          ${escapeHtml(currentJob.salary || "Not specified")}

        </p>


        <hr>


        <h2>
          Job Description
        </h2>


        <p class="long-text">

          ${escapeHtml(
            currentJob.description || "No job description available.",
          )}

        </p>


        <h2>
          Requirements
        </h2>


        <p class="long-text">

          ${escapeHtml(currentJob.requirements || "No requirements provided.")}

        </p>


        ${
          currentJob.application_url
            ? `

              <div
                class="job-external-link"
              >

                <a
                  href="${escapeHtml(currentJob.application_url)}"
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
    console.error("Could not load job:", error);

    container.innerHTML = `

      <p class="status-message error">

        Could not load job:

        ${escapeHtml(error.message)}

      </p>

    `;
  }
}

// Save job
async function saveJob() {
  const message = document.getElementById("job-action-message");

  if (!jobId || !message) {
    return;
  }

  try {
    message.className = "status-message info";

    message.textContent = "Saving job...";

    await saveJobAPI(jobId);

    message.className = "status-message success";

    message.textContent = "Job saved successfully.";
  } catch (error) {
    console.error("Save job error:", error);

    message.className = "status-message error";

    message.textContent = `Could not save job: ${error.message}`;
  }
}

// Apply
async function applyJob() {
  const message = document.getElementById("job-action-message");

  if (!jobId || !message) {
    return;
  }

  try {
    message.className = "status-message info";

    message.textContent = "Adding application...";

    await createApplication(jobId);

    message.className = "status-message success";

    message.textContent = "Application added successfully.";
  } catch (error) {
    console.error("Application error:", error);

    message.className = "status-message error";

    message.textContent = `Could not create application: ${error.message}`;
  }
}

// AI job analysis
async function analyseJob() {
  const container = document.getElementById("ai-analysis");

  if (!container || !jobId) {
    return;
  }

  if (analysing) {
    return;
  }

  analysing = true;

  container.innerHTML = `

    <p class="status-message info">

      Analysing job with AI...

    </p>

  `;

  try {
    const result = await analyseJobAPI(jobId);

    if (result && result.success === false) {
      throw new Error(result.error || "Analysis failed.");
    }

    renderAIAnalysis(result);
  } catch (error) {
    console.error("AI analysis error:", error);

    container.innerHTML = `

      <p class="status-message error">

        AI analysis failed:

        ${escapeHtml(error.message)}

      </p>

    `;
  } finally {
    analysing = false;
  }
}

// Render AI Approval
function renderAIApproval(chat, result) {
  if (!chat || !result) {
    return;
  }

  const approvalId = result.approval_id;

  if (!approvalId) {
    console.error("No approval ID returned by backend.");

    return;
  }

  chat.innerHTML += `

    <div
      class="ai-approval"
      data-approval-id="${escapeHtml(approvalId)}"
    >

      <div class="ai-approval-response">

        <strong>
          Career Agent:
        </strong>

        <p>
          ${escapeHtml(result.response || "No response received.")}
        </p>

      </div>


      <div class="ai-approval-review">

        <p>

          <strong>
            Human Review Required
          </strong>

        </p>


        <p>
          Is this AI response acceptable?
        </p>


        <div
          class="ai-approval-buttons"
        >

          <button
            type="button"
            class="primary-button"
            onclick="approveAIResponse('${escapeHtml(approvalId)}')"
          >
            Approve
          </button>


          <button
            type="button"
            class="secondary-button"
            onclick="showAIRejection('${escapeHtml(approvalId)}')"
          >
            Reject
          </button>

        </div>


        <div
          id="ai-rejection-${escapeHtml(approvalId)}"
          class="ai-rejection-form"
          style="display: none;"
        >

          <label
            for="ai-feedback-${escapeHtml(approvalId)}"
          >
            What should be improved?
          </label>


          <textarea
            id="ai-feedback-${escapeHtml(approvalId)}"
            rows="3"
            placeholder="Enter feedback for the Career Agent..."
          ></textarea>


          <button
            type="button"
            class="primary-button"
            onclick="rejectAIResponse('${escapeHtml(approvalId)}')"
          >
            Submit Feedback
          </button>

        </div>

      </div>

    </div>

  `;

  chat.scrollTop = chat.scrollHeight;
}

// Approve AI Response
async function approveAIResponse(approvalId) {
  const status = document.getElementById("chat-message");

  const approval = document.querySelector(
    `[data-approval-id="${CSS.escape(approvalId)}"]`,
  );

  if (status) {
    status.className = "status-message info";

    status.textContent = "Submitting approval...";
  }

  try {
    const result = await submitAIApproval(approvalId, true);

    if (!result.success) {
      throw new Error(result.error || "Approval failed.");
    }

    // Keep the AI response.
    // Only replace the review controls.
    if (approval) {
      const review = approval.querySelector(".ai-approval-review");

      if (review) {
        review.innerHTML = `

          <div
            class="status-message success"
          >

            <strong>
              ✓ AI response approved
            </strong>

          </div>

        `;
      }
    }

    if (status) {
      status.className = "status-message success";

      status.textContent = "AI response approved.";
    }
  } catch (error) {
    console.error("AI approval error:", error);

    if (status) {
      status.className = "status-message error";

      status.textContent = `Could not approve AI response: ${error.message}`;
    }
  }
}

// Show AI rejection form
function showAIRejection(approvalId) {
  const form = document.getElementById(`ai-rejection-${approvalId}`);

  if (!form) {
    return;
  }

  form.style.display = "block";

  const feedback = document.getElementById(`ai-feedback-${approvalId}`);

  if (feedback) {
    feedback.focus();
  }
}

async function rejectAIResponse(approvalId) {
  const feedbackElement = document.getElementById(`ai-feedback-${approvalId}`);

  const status = document.getElementById("chat-message");

  const approval = document.querySelector(
    `[data-approval-id="${CSS.escape(approvalId)}"]`,
  );

  if (!feedbackElement) {
    return;
  }

  const feedback = feedbackElement.value.trim();

  if (!feedback) {
    feedbackElement.focus();

    if (status) {
      status.className = "status-message error";

      status.textContent =
        "Please provide feedback before rejecting the response.";
    }

    return;
  }

  if (status) {
    status.className = "status-message info";

    status.textContent = "Sending feedback to Career Agent...";
  }

  // Disable buttons while processing.
  if (approval) {
    const buttons = approval.querySelectorAll("button");

    buttons.forEach((button) => {
      button.disabled = true;
    });
  }

  try {
    const result = await submitAIApproval(approvalId, false, feedback);

    if (!result.success) {
      throw new Error(result.error || "Could not submit feedback.");
    }

    // Mark it as rejected - keep all repsonses
    if (approval) {
      const review = approval.querySelector(".ai-approval-review");

      if (review) {
        review.innerHTML = `

          <div
            class="status-message error"
          >

            <strong>
              ✕ AI response rejected
            </strong>

            <p>
              <strong>
                Human feedback:
              </strong>
            </p>

            <p>
              ${escapeHtml(feedback)}
            </p>

          </div>

        `;
      }
    }

    // Append new response
    if (result.status === "awaiting_approval") {
      const chat = document.getElementById("chat-messages");

      if (chat) {
        renderAIApproval(chat, result);
      }
    }

    if (status) {
      status.className = "status-message info";

      status.textContent =
        "New AI response generated. Please review the new response.";
    }
  } catch (error) {
    console.error("AI rejection error:", error);

    // Re-enable buttons if something failed.
    if (approval) {
      const buttons = approval.querySelectorAll("button");

      buttons.forEach((button) => {
        button.disabled = false;
      });
    }

    if (status) {
      status.className = "status-message error";

      status.textContent = `Could not submit feedback: ${error.message}`;
    }
  }
}

// Agent chat
async function sendMessage() {
  const input = document.getElementById("chat-input");

  const chat = document.getElementById("chat-messages");

  const status = document.getElementById("chat-message");

  if (!input || !chat || !status) {
    return;
  }

  const message = input.value.trim();

  if (!message) {
    return;
  }

  // Add user message
  chat.innerHTML += `

    <div class="user-message">

      ${escapeHtml(message)}

    </div>

  `;

  input.value = "";

  status.className = "status-message info";

  status.textContent = "Career Agent is thinking...";

  try {
    const result = await sendChatMessage(message, jobId);

    if (!result.success) {
      throw new Error(result.error || "AI request failed.");
    }

    //Human review approvals in the loop
    if (result.status === "awaiting_approval") {
      renderAIApproval(chat, result);
    } else {
      // Normal AI response
      chat.innerHTML += `

        <div class="ai-message">

          ${escapeHtml(result.response || "No response received.")}

        </div>

      `;
    }

    status.className = "status-message";

    status.textContent = "";

    chat.scrollTop = chat.scrollHeight;
  } catch (error) {
    console.error("Career Agent error:", error);

    status.className = "status-message error";

    status.textContent = `Career Agent could not complete the request: ${error.message}`;
  }
}

// Enter to send
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("chat-input");

  if (!input) {
    return;
  }

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      sendMessage();
    }
  });
});

// Start
document.addEventListener("DOMContentLoaded", () => {
  loadJob();
});

const params = new URLSearchParams(window.location.search);

const jobId = params.get("id");

let currentJob = null;
let analysing = false;

// AI RESPONSE FORMATTER
function formatAIResponse(value) {
  if (value === null || value === undefined || value === "") {
    return `
      <p>
        No response received.
      </p>
    `;
  }

  const text = String(value).trim();

  // Escape HTML first.
  let safeText = escapeHtml(text);

  // Bold
  safeText = safeText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Inline code
  safeText = safeText.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Preserve line breaks
  safeText = safeText.replace(/\r?\n/g, "<br>");

  return `
    <div class="ai-response-text">
      ${safeText}
    </div>
  `;
}

// ANALYSIS DISPLAY
function displayAnalysis(value) {
  if (value === null || value === undefined || value === "") {
    return `
      <p class="analysis-empty">
        No information available.
      </p>
    `;
  }

  // Array
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return `
        <p class="analysis-empty">
          No information available.
        </p>
      `;
    }

    return `
      <ul class="analysis-list">

        ${value
          .map(
            (item) => `
              <li>
                ${escapeHtml(String(item))}
              </li>
            `,
          )
          .join("")}

      </ul>
    `;
  }

  // Object
  if (typeof value === "object") {
    return `
      <pre class="analysis-object">${escapeHtml(
        JSON.stringify(value, null, 2),
      )}</pre>
    `;
  }

  // Primitive
  return `
    <p>
      ${escapeHtml(String(value))}
    </p>
  `;
}

// RENDER AI JOB ANALYSIS

function renderAIAnalysis(result) {
  const container = document.getElementById("ai-analysis");

  if (!container) {
    return;
  }

  if (!result) {
    container.innerHTML = `
      <p class="status-message error">
        No analysis received.
      </p>
    `;

    return;
  }

  const analysis =
    result.analysis && typeof result.analysis === "object"
      ? result.analysis
      : result;

  container.innerHTML = `
    <div class="analysis-grid">

      <div class="analysis-card">

        <h3>
          Skills
        </h3>

        ${displayAnalysis(analysis.skills)}

      </div>


      <div class="analysis-card">

        <h3>
          Qualifications
        </h3>

        ${displayAnalysis(analysis.qualifications)}

      </div>


      <div class="analysis-card">

        <h3>
          Experience
        </h3>

        ${displayAnalysis(analysis.experience)}

      </div>


      <div class="analysis-card">

        <h3>
          ATS Keywords
        </h3>

        ${displayAnalysis(analysis.ats_keywords)}

      </div>


      <div class="analysis-card analysis-summary">

        <h3>
          Summary
        </h3>

        ${displayAnalysis(analysis.summary)}

      </div>

    </div>
  `;
}

// LOAD JOB
async function loadJob() {
  const container = document.getElementById("job-details");

  if (!container) {
    return;
  }

  // validate id
  if (!jobId) {
    container.innerHTML = `
      <p class="status-message error">
        No job selected.
      </p>
    `;

    return;
  }

  // fetch job
  try {
    currentJob = await getJob(jobId);

    if (!currentJob) {
      throw new Error("Job not found.");
    }

    // render job
    container.innerHTML = `
      <article class="job-detail-card">

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
          <strong>Location:</strong>
          ${escapeHtml(currentJob.location || "Location not specified")}
        </p>


        <p>
          <strong>Industry:</strong>
          ${escapeHtml(currentJob.industry || "Not specified")}
        </p>


        <p>
          <strong>Job Type:</strong>
          ${escapeHtml(currentJob.job_type || "Not specified")}
        </p>


        <p>
          <strong>Salary:</strong>
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
              <div class="job-external-link">

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

        ${escapeHtml(error.message || "Unknown error")}

      </p>
    `;
  }
}

// SAVE JOB
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

    message.textContent = `Could not save job: ${
      error.message || "Unknown error"
    }`;
  }
}

// APPLY TO JOB
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

    message.textContent = `Could not create application: ${
      error.message || "Unknown error"
    }`;
  }
}

// AI JOB ANALYSIS
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

        ${escapeHtml(error.message || "Unknown error")}

      </p>
    `;
  } finally {
    analysing = false;
  }
}

// CAREER AGENT RESPONSE
function renderCareerAgentResponse(result) {
  if (!result) {
    return `
      <div class="ai-response-content">

        <div class="ai-response-text">

          <p>
            No response received.
          </p>

        </div>

      </div>
    `;
  }

  // AI response
  const response =
    result.response ||
    result.message ||
    result.answer ||
    "No response received.";

  // sources
  let sources = [];

  if (result.rag && Array.isArray(result.rag.sources)) {
    sources = result.rag.sources;
  } else if (Array.isArray(result.sources)) {
    sources = result.sources;
  } else if (result.result && Array.isArray(result.result.sources)) {
    sources = result.result.sources;
  } else if (result.data && Array.isArray(result.data.sources)) {
    sources = result.data.sources;
  }

  // Clean source list
  sources = [
    ...new Set(
      sources
        .filter((source) => source !== null && source !== undefined)
        .map((source) => String(source).trim())
        .filter(Boolean),
    ),
  ];

  // Confidence
  const confidence =
    result.rag && result.rag.confidence ? result.rag.confidence : null;

  // RAG source UI
  const sourcesHTML =
    sources.length > 0
      ? `
        <div class="rag-sources">

          <div class="rag-sources-header">

            <span>
              Career Knowledge Sources
            </span>

            ${
              confidence
                ? `
                  <span class="rag-confidence">
                    Confidence:
                    ${escapeHtml(confidence)}
                  </span>
                `
                : ""
            }

          </div>


          <div class="rag-source-tags">

            ${sources
              .map(
                (source) => `
                  <span
                    class="rag-source-tag"
                  >
                    ${escapeHtml(source)}
                  </span>
                `,
              )
              .join("")}

          </div>

        </div>
      `
      : "";

  // Final response
  return `
    <div class="ai-response-content">

      <div class="ai-response-text">

        ${formatAIResponse(response)}

      </div>


      ${sourcesHTML}

    </div>
  `;
}

// HUMAN APPROVAL
function renderAIApproval(chat, result) {
  if (!chat || !result) {
    return;
  }

  const approvalId = result.approval_id;

  if (!approvalId) {
    chat.innerHTML += `
      <div class="ai-message">

        <div class="ai-message-header">

          <strong>
            Career Agent
          </strong>

        </div>


        ${renderCareerAgentResponse(result)}

      </div>
    `;

    chat.scrollTop = chat.scrollHeight;

    return;
  }

  const safeApprovalId = escapeHtml(String(approvalId));

  chat.innerHTML += `
    <div
      class="ai-approval"
      data-approval-id="${safeApprovalId}"
    >

      <div class="ai-approval-response">

        <div class="ai-message-header">

          <strong>
            Career Agent
          </strong>

        </div>


        ${renderCareerAgentResponse(result)}

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


        <div class="ai-approval-buttons">

          <button
            type="button"
            class="primary-button"
            onclick="approveAIResponse('${safeApprovalId}')"
          >
            Approve
          </button>


          <button
            type="button"
            class="secondary-button"
            onclick="showAIRejection('${safeApprovalId}')"
          >
            Reject
          </button>

        </div>


        <div
          id="ai-rejection-${safeApprovalId}"
          class="ai-rejection-form"
          style="display: none;"
        >

          <label
            for="ai-feedback-${safeApprovalId}"
          >
            What should be improved?
          </label>


          <textarea
            id="ai-feedback-${safeApprovalId}"
            rows="3"
            placeholder="Enter feedback for the Career Agent..."
          ></textarea>


          <button
            type="button"
            class="primary-button"
            onclick="rejectAIResponse('${safeApprovalId}')"
          >
            Submit Feedback
          </button>

        </div>

      </div>

    </div>
  `;

  chat.scrollTop = chat.scrollHeight;
}

// APPROVE AI RESPONSE
async function approveAIResponse(approvalId) {
  const status = document.getElementById("chat-message");

  const approval = document.querySelector(
    `[data-approval-id="${CSS.escape(String(approvalId))}"]`,
  );

  if (status) {
    status.className = "status-message info";

    status.textContent = "Submitting approval...";
  }

  try {
    const result = await submitAIApproval(approvalId, true);

    if (!result || result.success === false) {
      throw new Error(result?.error || "Approval failed.");
    }

    if (approval) {
      const review = approval.querySelector(".ai-approval-review");

      if (review) {
        review.innerHTML = `
          <div class="status-message success">

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

      status.textContent = `Could not approve AI response: ${
        error.message || "Unknown error"
      }`;
    }
  }
}

// SHOW REJECTION
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

// REJECT AI RESPONSE
async function rejectAIResponse(approvalId) {
  const feedbackElement = document.getElementById(`ai-feedback-${approvalId}`);

  const status = document.getElementById("chat-message");

  const approval = document.querySelector(
    `[data-approval-id="${CSS.escape(String(approvalId))}"]`,
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

  // Disable approval controls
  if (approval) {
    const buttons = approval.querySelectorAll("button");

    buttons.forEach((button) => {
      button.disabled = true;
    });
  }

  try {
    const result = await submitAIApproval(approvalId, false, feedback);

    if (!result || result.success === false) {
      throw new Error(result?.error || "Could not submit feedback.");
    }

    // Mark old response as rejected
    if (approval) {
      const review = approval.querySelector(".ai-approval-review");

      if (review) {
        review.innerHTML = `
          <div class="status-message error">

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

    // Render regenerated response
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

    // Re-enable buttons
    if (approval) {
      const buttons = approval.querySelectorAll("button");

      buttons.forEach((button) => {
        button.disabled = false;
      });
    }

    if (status) {
      status.className = "status-message error";

      status.textContent = `Could not submit feedback: ${
        error.message || "Unknown error"
      }`;
    }
  }
}

// Multi-agent workflow
let careerWorkflowBusy = false;

function renderCareerWorkflowResult(result) {
  const chat = document.getElementById("chat-messages");

  if (!chat || !result) return;

  const planner = result.planner_result || {};
  const worker = result.worker_result || {};
  const reviewer = result.reviewer_result || {};
  const review = result.human_review || {};

  const workflowId = String(result.workflow_id || "");
  const pending = result.status === "pending_human_review";

  const section = (heading, content) => `
        <section class="workflow-result-section">
            <h4>${escapeHtml(heading)}</h4>
            <div>${displayAnalysis(content)}</div>
        </section>
    `;

  const decisionUI =
    pending && workflowId
      ? `
            <div class="workflow-human-review">
                <h4>Human Review Required</h4>
                <p>Review the multi-agent results before making a decision.</p>

                <label for="career-review-reason">Review comments</label>
                <textarea
                    id="career-review-reason"
                    rows="3"
                    maxlength="2000"
                    placeholder="Explain your decision or suggest improvements."
                ></textarea>

                <div class="workflow-decision-buttons">
                    <button
                        type="button"
                        class="primary-button"
                        onclick="decideCareerWorkflow('Accept')"
                    >Accept</button>

                    <button
                        type="button"
                        class="secondary-button"
                        onclick="decideCareerWorkflow('Partially Accept')"
                    >Partially Accept</button>

                    <button
                        type="button"
                        class="danger-button"
                        onclick="decideCareerWorkflow('Reject')"
                    >Reject</button>
                </div>

                <p class="workflow-review-status status-message"
                   aria-live="polite"></p>
            </div>
        `
      : `
            <div class="workflow-review-complete">
                <strong>Human review: ${escapeHtml(
                  review.decision ||
                    review.status ||
                    result.status ||
                    "Unknown",
                )}</strong>
                ${review.reason ? `<p>${escapeHtml(review.reason)}</p>` : ""}
            </div>
        `;

  chat.insertAdjacentHTML(
    "beforeend",
    `
        <div class="ai-message multi-agent-message"
             data-workflow-id="${escapeHtml(workflowId)}">

            <div class="ai-message-header">
                <strong>Career Multi-Agent System</strong>
            </div>

            <p class="workflow-id">
                Workflow ID: ${escapeHtml(workflowId || "Unavailable")}
            </p>

            <span class="tag">
                ${escapeHtml(result.status || "Unknown status")}
            </span>

            ${section("Planner", planner.plan || "No plan returned.")}

            ${section(
              "Worker",
              worker.result || worker.answer || "No worker result returned.",
            )}

            ${section(
              "Evidence used",
              worker.evidence_used || worker.evidence_used_ids || [],
            )}

            ${section(
              "Missing information",
              worker.missing_information || worker.missing_evidence || [],
            )}

            ${section("Reviewer risk", reviewer.risk || "Not provided.")}

            ${section(
              "Reviewer recommendation",
              reviewer.recommendation || "Not provided.",
            )}

            ${
              review.correction
                ? section(
                    "Reviewer correction",
                    reviewer.correction || review.correction,
                  )
                : ""
            }

            ${decisionUI}
        </div>
    `,
  );

  chat.scrollTop = chat.scrollHeight;
}

// multi-agent workflow human decision
async function decideCareerWorkflow(decision) {
  const chat = document.getElementById("chat-messages");
  const status = document.getElementById("chat-message");

  if (careerWorkflowBusy || !chat) return;

  const card = chat.querySelector(".multi-agent-message:last-of-type");

  if (!card) return;

  const workflowId = card.dataset.workflowId;

  if (!workflowId) {
    if (status) {
      status.className = "status-message error";
      status.textContent = "Workflow ID is missing.";
    }
    return;
  }

  const reasonField = card.querySelector("#career-review-reason");
  const reason = reasonField ? reasonField.value.trim() : "";
  const reviewStatus = card.querySelector(".workflow-review-status");
  const buttons = card.querySelectorAll(".workflow-decision-buttons button");

  careerWorkflowBusy = true;
  buttons.forEach((button) => (button.disabled = true));

  if (reviewStatus) {
    reviewStatus.className = "workflow-review-status status-message info";
    reviewStatus.textContent = "Submitting your decision...";
  }

  try {
    const result = await submitCareerWorkflowDecisionAPI(
      workflowId,
      decision,
      reason,
    );

    if (result.status !== "completed") {
      throw new Error("The workflow did not complete the review.");
    }

    // Replace the pending-review controls with the completed decision.
    const review = card.querySelector(".workflow-human-review");

    if (review) {
      review.innerHTML = `
                <div class="workflow-review-complete">
                    <strong>Review completed: ${escapeHtml(decision)}</strong>
                    <p>${escapeHtml(reason || "No comments provided.")}</p>
                </div>
            `;
    }

    if (status) {
      status.className = "status-message success";
      status.textContent = `Career workflow decision submitted: ${decision}.`;
    }
  } catch (error) {
    buttons.forEach((button) => (button.disabled = false));

    if (reviewStatus) {
      reviewStatus.className = "workflow-review-status status-message error";
      reviewStatus.textContent =
        error.message || "Could not submit your decision.";
    }
  } finally {
    careerWorkflowBusy = false;
  }
}

// Send multi-agent mode messages
async function sendMultiAgentCareerMessage(message) {
  if (!currentJob || !currentJob.id) {
    throw new Error("Load a job before starting the multi-agent workflow.");
  }

  const result = await runCareerWorkflowAPI(message, currentJob, {});

  renderCareerWorkflowResult(result);
  return result;
}

// CAREER AGENT CHAT
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

  // Prevent duplicate submissions.
  if (input.disabled) {
    return;
  }

  // Display the user's message safely.
  chat.insertAdjacentHTML(
    "beforeend",
    `<div class="user-message">${escapeHtml(message)}</div>`,
  );

  input.value = "";

  status.className = "status-message info";
  status.textContent = "Career Agent is thinking...";

  input.disabled = true;

  const sendButton = document.querySelector(".chat-input button");

  if (sendButton) {
    sendButton.disabled = true;
  }

  try {
    const mode =
      document.getElementById("career-agent-mode")?.value || "career_agent";

    // Multi-agent workflow.
    if (mode === "multi_agent" || mode === "multi-agent") {
      await sendMultiAgentCareerMessage(message);

      status.className = "status-message";
      status.textContent = "";

      return;
    }

    const result = await sendChatMessage(message, currentJob?.id ?? jobId);

    if (!result || result.success === false) {
      throw new Error(
        result?.error || "The Career Agent returned no valid response.",
      );
    }

    if (result.status === "awaiting_approval") {
      renderAIApproval(chat, result);
    } else {
      chat.insertAdjacentHTML(
        "beforeend",
        `
          <div class="ai-message">
            <div class="ai-message-header">
              <strong>Career Agent</strong>
            </div>
            ${renderCareerAgentResponse(result)}
          </div>
        `,
      );
    }

    status.className = "status-message";
    status.textContent = "";

    chat.scrollTop = chat.scrollHeight;
  } catch (error) {
    console.error("Career Agent error:", error);

    status.className = "status-message error";
    status.textContent = `Career Agent could not complete the request: ${
      error.message || "Unknown error"
    }`;
  } finally {
    input.disabled = false;

    if (sendButton) {
      sendButton.disabled = false;
    }

    input.focus();
  }
}

// ENTER TO SEND
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

// MODE SELECTION
document.addEventListener("DOMContentLoaded", () => {
  const modeSelector = document.getElementById("career-agent-mode");
  const description = document.getElementById("career-mode-description");

  if (!modeSelector || !description) return;

  function updateDescription() {
    if (modeSelector.value === "multi_agent") {
      description.textContent =
        "Uses Planner, Worker and Reviewer agents, followed by your review.";
    } else {
      description.textContent =
        "Chat with the Career Agent for personalised job guidance.";
    }
  }

  modeSelector.addEventListener("change", updateDescription);
  updateDescription();
});

// PAGE START
document.addEventListener("DOMContentLoaded", () => {
  loadJob();
});

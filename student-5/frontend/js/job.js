// Supports:
// - Selected job context
// - Job details
// - Save job
// - Apply to job
// - AI job analysis
// - Career Agent chat
// - MCP/RAG backend responses
// - Organisation knowledge TXT sources
// - RAG confidence
// - Human approval workflow

// SELECTED JOB
const params = new URLSearchParams(window.location.search);
const jobId = params.get("id");

let currentJob = null;
let analysing = false;

// AI MARKDOWN
function formatAIResponse(value) {
  if (value === null || value === undefined || value === "") {
    return "<p>No response received.</p>";
  }

  const text = String(value).trim();
  const lines = text.split(/\r?\n/);

  let html = "";
  let inList = false;
  let listType = null;

  function closeList() {
    if (!inList) {
      return;
    }

    html += listType === "ol" ? "</ol>" : "</ul>";

    inList = false;
    listType = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // Empty line
    if (!line) {
      closeList();
      continue;
    }

    // --------------------------------------------------------
    // H3 markdown: ### Heading
    // --------------------------------------------------------

    if (line.startsWith("### ")) {
      closeList();

      html += `
        <h4>
          ${escapeHtml(line.substring(4))}
        </h4>
      `;

      continue;
    }

    // --------------------------------------------------------
    // H2 markdown: ## Heading
    // --------------------------------------------------------

    if (line.startsWith("## ")) {
      closeList();

      html += `
        <h3>
          ${escapeHtml(line.substring(3))}
        </h3>
      `;

      continue;
    }

    // --------------------------------------------------------
    // H1 markdown: # Heading
    // --------------------------------------------------------

    if (line.startsWith("# ")) {
      closeList();

      html += `
        <h2>
          ${escapeHtml(line.substring(2))}
        </h2>
      `;

      continue;
    }

    // --------------------------------------------------------
    // Unordered list
    // - item
    // * item
    // --------------------------------------------------------

    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList || listType !== "ul") {
        closeList();

        html += "<ul>";

        inList = true;
        listType = "ul";
      }

      const item = line.replace(/^[-*]\s+/, "");

      html += `
        <li>
          ${formatInlineAIText(item)}
        </li>
      `;

      continue;
    }

    // --------------------------------------------------------
    // Ordered list
    // 1. item
    // 2. item
    // --------------------------------------------------------

    if (/^\d+\.\s+/.test(line)) {
      if (!inList || listType !== "ol") {
        closeList();

        html += "<ol>";

        inList = true;
        listType = "ol";
      }

      const item = line.replace(/^\d+\.\s+/, "");

      html += `
        <li>
          ${formatInlineAIText(item)}
        </li>
      `;

      continue;
    }

    // --------------------------------------------------------
    // Normal paragraph
    // --------------------------------------------------------

    closeList();

    html += `
      <p>
        ${formatInlineAIText(line)}
      </p>
    `;
  }

  closeList();

  return html;
}

// ============================================================
// INLINE AI TEXT
// ============================================================

function formatInlineAIText(value) {
  let text = escapeHtml(String(value));

  // Bold: **text**
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Inline code: `text`
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

  return text;
}

// ============================================================
// ANALYSIS DISPLAY
// ============================================================

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

  // String / number / boolean
  return `
    <p>
      ${escapeHtml(String(value))}
    </p>
  `;
}

// ============================================================
// RENDER AI JOB ANALYSIS
// ============================================================

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

  // Some backends return:
  //
  // {
  //   success: true,
  //   skills: [...],
  //   qualifications: [...],
  //   experience: [...],
  //   ats_keywords: [...],
  //   summary: "..."
  // }
  //
  // Others may wrap this under result.analysis.
  //
  const analysis =
    result.analysis && typeof result.analysis === "object"
      ? result.analysis
      : result;

  container.innerHTML = `
    <div class="analysis-grid">

      <div class="analysis-card">
        <h3>Skills</h3>

        ${displayAnalysis(analysis.skills)}
      </div>


      <div class="analysis-card">
        <h3>Qualifications</h3>

        ${displayAnalysis(analysis.qualifications)}
      </div>


      <div class="analysis-card">
        <h3>Experience</h3>

        ${displayAnalysis(analysis.experience)}
      </div>


      <div class="analysis-card">
        <h3>ATS Keywords</h3>

        ${displayAnalysis(analysis.ats_keywords)}
      </div>


      <div class="analysis-card analysis-summary">
        <h3>Summary</h3>

        ${displayAnalysis(analysis.summary)}
      </div>

    </div>
  `;
}

// ============================================================
// LOAD JOB
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

// ============================================================
// SAVE JOB
// ============================================================

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

// ============================================================
// APPLY TO JOB
// ============================================================

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

// ============================================================
// AI JOB ANALYSIS
// ============================================================

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

// Career agent reponse
function renderCareerAgentResponse(result) {
  if (!result) {
    return `
      <div class="ai-response-content">
        <div class="ai-response-text">
          <p>No response received.</p>
        </div>
      </div>
    `;
  }

  const response =
    result.response ||
    result.message ||
    result.answer ||
    "No response received.";

  /*
   * Sources can potentially be returned in different places
   * depending on which backend endpoint generated the response.
   *
   * Normal /api/ai/chat response:
   *
   * result.sources
   *
   * Possible nested response:
   *
   * result.result.sources
   * result.data.sources
   * result.analysis.sources
   *
   * We check these without treating TXT files as URLs.
   */

  let sources = [];

  if (Array.isArray(result.sources)) {
    sources = result.sources;
  } else if (result.result && Array.isArray(result.result.sources)) {
    sources = result.result.sources;
  } else if (result.data && Array.isArray(result.data.sources)) {
    sources = result.data.sources;
  } else if (result.analysis && Array.isArray(result.analysis.sources)) {
    sources = result.analysis.sources;
  }

  /*
   * Confidence can also potentially be nested.
   */

  const confidence =
    result.confidence ||
    result.result?.confidence ||
    result.data?.confidence ||
    result.analysis?.confidence ||
    null;

  return `
    <div class="ai-response-content">

      <div class="ai-response-text">
        ${formatAIResponse(response)}
      </div>

      ${
        confidence
          ? `
            <div class="rag-confidence">

              <span>
                RAG confidence:
              </span>

              <strong>
                ${escapeHtml(String(confidence))}
              </strong>

            </div>
          `
          : ""
      }
    </div>
  `;
}

// Human AI approval
function renderAIApproval(chat, result) {
  if (!chat || !result) {
    return;
  }

  const approvalId = result.approval_id;

  // Backend does not require approval
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

// ============================================================
// APPROVE AI RESPONSE
// ============================================================

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

      status.textContent = `Could not approve AI response: ${
        error.message || "Unknown error"
      }`;
    }
  }
}

// ============================================================
// SHOW REJECTION FORM
// ============================================================

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

// ============================================================
// REJECT AI RESPONSE
// ============================================================

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

  // Disable buttons while processing.

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

    // Mark original response as rejected.
    // Keep the original response visible.

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

    // --------------------------------------------------------
    // Backend may return a new response requiring approval.
    // --------------------------------------------------------

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

    // Re-enable buttons if request failed.

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

// ============================================================
// CAREER AGENT CHAT
// ============================================================

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

  // ----------------------------------------------------------
  // Display user message
  // ----------------------------------------------------------

  chat.innerHTML += `
    <div class="user-message">

      ${escapeHtml(message)}

    </div>
  `;

  input.value = "";

  status.className = "status-message info";

  status.textContent = "Career Agent is thinking...";

  // Disable input while waiting.

  input.disabled = true;

  const sendButton = document.querySelector(".chat-input button");

  if (sendButton) {
    sendButton.disabled = true;
  }

  try {
    // --------------------------------------------------------
    // Send selected job ID to backend.
    //
    // Backend then:
    // 1. Loads selected job
    // 2. Executes MCP/RAG
    // 3. Retrieves organisation TXT files
    // 4. Sends context to AI
    // 5. Returns response + sources
    // --------------------------------------------------------

    const result = await sendChatMessage(message, jobId);

    if (!result || result.success === false) {
      throw new Error(result?.error || "AI request failed.");
    }

    // --------------------------------------------------------
    // Human approval workflow
    // --------------------------------------------------------

    if (result.status === "awaiting_approval") {
      renderAIApproval(chat, result);
    } else {
      // ------------------------------------------------------
      // Normal AI response
      //
      // IMPORTANT:
      //
      // Do NOT use escapeHtml(result.response) here.
      //
      // That would hide:
      // - formatted AI markdown
      // - RAG confidence
      // - TXT source list
      //
      // renderCareerAgentResponse() handles all of it.
      // ------------------------------------------------------

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

// ============================================================
// ENTER TO SEND
// ============================================================

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

// Page start
document.addEventListener("DOMContentLoaded", () => {
  loadJob();
});

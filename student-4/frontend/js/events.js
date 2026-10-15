let events = [];

const grid = document.getElementById("eventGrid");
const search = document.getElementById("search");
const count = document.getElementById("count");

/* =========================
   GUEST / ADMIN MODE
   ========================= */

const guestView = document.getElementById("guestView");
const adminView = document.getElementById("adminView");

const modeButton = document.getElementById("modeButton");
const modeLabel = document.getElementById("modeLabel");

const adminEventTable = document.getElementById("adminEventTable");
const adminCount = document.getElementById("adminCount");
const adminSearch = document.getElementById("adminSearch");

let currentMode = "guest";
let editingEventId = null;


/* =========================
   LOAD EVENTS
   ========================= */

async function loadEvents() {
  try {
    const response = await fetch("/api/events");

    if (!response.ok) {
      throw new Error("Failed to load events.");
    }

    events = await response.json();

    render();
  } catch (error) {
    console.error("Error loading events:", error);

    if (count) {
      count.textContent = "Unable to load events.";
    }

    if (adminCount) {
      adminCount.textContent = "Unable to load events.";
    }
  }
}


/* =========================
   DATE HELPERS
   ========================= */

function prettyDate(value) {
  const d = new Date(value + "T00:00:00");

  return d
    .toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
    })
    .toUpperCase();
}


function fullDate(value) {
  const d = new Date(value + "T00:00:00");

  return d.toLocaleDateString("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}


function withinRange(eventDate, mode) {
  if (!mode) return true;

  /*
    For the current project demo data,
    7 August 2026 is used as the reference date.
  */
  const today = new Date("2026-08-07T00:00:00");
  const d = new Date(eventDate + "T00:00:00");

  const diffDays = Math.floor(
    (d - today) / 86400000,
  );

  if (mode === "week") {
    return diffDays >= 0 && diffDays <= 7;
  }

  if (mode === "month") {
    return (
      d.getMonth() === today.getMonth() &&
      d.getFullYear() === today.getFullYear()
    );
  }

  return true;
}


/* =========================
   GUEST VIEW
   ========================= */

function render() {
  const q = search.value
    .trim()
    .toLowerCase();

  const filtered = events.filter((e) => {
    const text =
      `${e.title} ${e.category} ${e.location} ${e.description}`.toLowerCase();

    return !q || text.includes(q);
  });

  count.textContent =
    `${filtered.length} event${
      filtered.length === 1 ? "" : "s"
    }`;

  grid.innerHTML = filtered
    .map(
      (e) => `
        <article class="card">
          <div class="image">
            <span class="emoji">
              ${e.emoji || "📅"}
            </span>

            <span class="tag">
              ${e.category}
            </span>

            <span class="date-pill">
              ${prettyDate(e.date)}
            </span>
          </div>

          <div class="content">
            <h3>${e.title}</h3>

            <p>
              ${e.description}
            </p>

            <div class="meta">
              <span>
                📍 ${e.location}
              </span>

              <span>
                📅 ${fullDate(e.date)}
              </span>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}


/* =========================
   MODE SWITCH
   ========================= */

function toggleMode() {
  if (currentMode === "guest") {
    showAdminMode();
  } else {
    showGuestMode();
  }
}


function showAdminMode() {
  currentMode = "admin";

  guestView.style.display = "none";

  adminView.classList.add("active");

  modeLabel.textContent = "Admin";

  modeButton.classList.add("admin");

  toggleChat(false);

  renderAdmin();

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}


function showGuestMode() {
  currentMode = "guest";

  guestView.style.display = "block";

  adminView.classList.remove("active");

  modeLabel.textContent = "Guest";

  modeButton.classList.remove("admin");

  render();

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}


/* =========================
   ADMIN VIEW
   ========================= */

function renderAdmin() {
  if (!adminEventTable) return;

  const q = adminSearch.value
    .trim()
    .toLowerCase();

  const filtered = events.filter((e) => {
    const text =
      `${e.title} ${e.category} ${e.location} ${e.description}`.toLowerCase();

    return !q || text.includes(q);
  });

  adminCount.textContent =
    `${filtered.length} event${
      filtered.length === 1 ? "" : "s"
    }`;

  if (filtered.length === 0) {
    adminEventTable.innerHTML = `
      <tr>
        <td
          colspan="5"
          style="
            text-align:center;
            padding:40px 20px;
            color:#667085;
          "
        >
          No events found.
        </td>
      </tr>
    `;

    return;
  }

  adminEventTable.innerHTML = filtered
    .map(
      (e) => `
        <tr>

          <td>
            <div class="admin-event-name">

              <div class="admin-event-icon">
                ${e.emoji || "📅"}
              </div>

              <div>
                <div class="admin-event-title">
                  ${e.title}
                </div>

                <div class="admin-event-location">
                  ${e.description}
                </div>
              </div>

            </div>
          </td>

          <td>
            <span class="admin-category-pill">
              ${e.category}
            </span>
          </td>

          <td>
            ${prettyDate(e.date)}
          </td>

          <td>
            ${e.location}
          </td>

          <td>
            <div class="admin-actions">

              <button
                class="admin-action-btn"
                type="button"
                onclick="editEvent(${e.id})"
              >
                Edit
              </button>

              <button
                class="admin-action-btn delete"
                type="button"
                onclick="deleteEvent(${e.id})"
              >
                Delete
              </button>

            </div>
          </td>

        </tr>
      `,
    )
    .join("");
}


/* =========================
   ADMIN ACTIONS
   ========================= */

function editEvent(id) {
  const eventItem =
    events.find((e) => e.id === id);

  if (!eventItem) return;

  editingEventId = id;

  document.getElementById(
    "eventTitle",
  ).value = eventItem.title || "";

  document.getElementById(
    "eventCategory",
  ).value = eventItem.category || "";

  document.getElementById(
    "eventDate",
  ).value = eventItem.date || "";

  document.getElementById(
    "eventLocation",
  ).value = eventItem.location || "";

  document.getElementById(
    "eventDescription",
  ).value = eventItem.description || "";

  const emojiInput =
    document.getElementById("eventEmoji");

  if (emojiInput) {
    emojiInput.value =
      eventItem.emoji || "";
  }

  const modalTitle =
    document.getElementById(
      "eventModalTitle",
    );

  const submitButton =
    document.getElementById(
      "eventSubmitButton",
    );

  const modal =
    document.getElementById(
      "eventModal",
    );

  if (modalTitle) {
    modalTitle.textContent =
      "Edit Event";
  }

  if (submitButton) {
    submitButton.textContent =
      "Save Changes";
  }

  if (modal) {
    modal.classList.add("open");
  }

  document.body.style.overflow =
    "hidden";
}


async function deleteEvent(id) {
  const eventItem =
    events.find((e) => e.id === id);

  if (!eventItem) return;

  const confirmed =
    window.confirm(
      `Are you sure you want to delete "${eventItem.title}"?\n\nThis action cannot be undone.`,
    );

  if (!confirmed) return;

  try {
    const response =
      await fetch(
        `/api/events/${id}`,
        {
          method: "DELETE",
        },
      );

    const result =
      await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ||
        "Failed to delete event.",
      );
    }

    await loadEvents();

    renderAdmin();
  } catch (error) {
    console.error(
      "Delete event error:",
      error,
    );

    alert(
      error.message ||
      "Unable to delete the event.",
    );
  }
}


/* =========================
   CHAT
   ========================= */

function toggleChat(force) {
  const chat =
    document.getElementById("chat");

  if (!chat) return;

  const open =
    typeof force === "boolean"
      ? force
      : !chat.classList.contains("open");

  chat.classList.toggle(
    "open",
    open,
  );

  if (open) {
    setTimeout(() => {
      const chatInput =
        document.getElementById("chatInput");

      if (chatInput) {
        chatInput.focus();
      }
    }, 100);
  }
}


function addMessage(text, type) {
  const messages =
    document.getElementById("messages");

  const div =
    document.createElement("div");

  div.className =
    `msg ${type}`;

  div.textContent =
    text;

  messages.appendChild(div);

  messages.scrollTop =
    messages.scrollHeight;
}




//请求ai回答
async function sendMessage() {

  //找到聊天输入框 → 拿到用户输入 → 如果空的就不发送。
  const input =
    document.getElementById("chatInput");

  const text =
    input.value.trim();

  if (!text) return;

  addMessage(
    text,
    "user",
  );

  input.value = "";

  const response = await fetch("/api/ai", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message: text
    })
  });

  const data = await response.json();

  addMessage(
    data.response,
    "bot",
  );

}



function askQuick(text) {
  toggleChat(true);

  document.getElementById(
    "chatInput",
  ).value = text;

  sendMessage();
}


/* =========================
   EVENT MODAL
   ========================= */

function openEventModal() {
  editingEventId = null;

  const modal =
    document.getElementById(
      "eventModal",
    );

  const title =
    document.getElementById(
      "eventModalTitle",
    );

  const submitButton =
    document.getElementById(
      "eventSubmitButton",
    );

  const form =
    document.getElementById(
      "eventForm",
    );

  if (!modal) return;

  if (form) {
    form.reset();
  }

  if (title) {
    title.textContent =
      "Add Event";
  }

  if (submitButton) {
    submitButton.textContent =
      "Add Event";
  }

  modal.classList.add("open");

  document.body.style.overflow =
    "hidden";
}


function closeEventModal() {
  const modal =
    document.getElementById(
      "eventModal",
    );

  if (!modal) return;

  modal.classList.remove("open");

  document.body.style.overflow =
    "";

  const form =
    document.getElementById(
      "eventForm",
    );

  if (form) {
    form.reset();
  }

  editingEventId = null;
}


/* =========================
   CREATE / UPDATE EVENT
   ========================= */

async function createEvent(event) {
  event.preventDefault();

  const title =
    document
      .getElementById("eventTitle")
      .value
      .trim();

  const category =
    document
      .getElementById("eventCategory")
      .value
      .trim();

  const date =
    document
      .getElementById("eventDate")
      .value;

  const location =
    document
      .getElementById("eventLocation")
      .value
      .trim();

  const description =
    document
      .getElementById("eventDescription")
      .value
      .trim();

  const emoji =
  document
    .getElementById("eventEmoji")
    .value
    .trim();

  if (
    !title ||
    !category ||
    !date ||
    !location ||
    !description
  ) {
    alert(
      "Please complete all required fields.",
    );

    return;
  }

  const eventData = {
    title,
    category,
    date,
    location,
    description,
    emoji,
  };

  try {
    const isEditing =
      editingEventId !== null;

    const url = isEditing
      ? `/api/events/${editingEventId}`
      : "/api/events";

    const method = isEditing
      ? "PUT"
      : "POST";

    const response =
      await fetch(
        url,
        {
          method,

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify(
            eventData,
          ),
        },
      );

    const result =
      await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ||
        "Unable to save event.",
      );
    }

    closeEventModal();

    await loadEvents();

    renderAdmin();
  } catch (error) {
    console.error(
      "Save event error:",
      error,
    );

    alert(
      error.message ||
      "Unable to save the event.",
    );
  }
}


/* =========================
   EVENT LISTENERS
   ========================= */

const eventForm =
  document.getElementById(
    "eventForm",
  );

if (eventForm) {
  eventForm.addEventListener(
    "submit",
    createEvent,
  );
}


const eventModal =
  document.getElementById(
    "eventModal",
  );

if (eventModal) {
  eventModal.addEventListener(
    "click",
    (event) => {
      if (event.target === eventModal) {
        closeEventModal();
      }
    },
  );
}


/* Guest search */

search.addEventListener(
  "input",
  render,
);


/* Admin search */

if (adminSearch) {
  adminSearch.addEventListener(
    "input",
    renderAdmin,
  );
}


/* =========================
   INITIAL LOAD
   ========================= */

loadEvents();


/* ==========================================
   RELEASE 2 - EVENT MULTI-AGENT SYSTEM
   Planner -> Worker -> Reviewer -> Human
   ========================================== */

let currentAgentWorkflowId = null;
let agentBusy = false;

const agentRequestInput =
  document.getElementById("agentRequest");

const runAgentButton =
  document.getElementById("runAgentButton");

const agentStatus =
  document.getElementById("agentStatus");

const agentResults =
  document.getElementById("agentResults");

const plannerOutput =
  document.getElementById("plannerOutput");

const workerOutput =
  document.getElementById("workerOutput");

const reviewerOutput =
  document.getElementById("reviewerOutput");

const reviewReason =
  document.getElementById("reviewReason");

const humanReviewStatus =
  document.getElementById("humanReviewStatus");

const reviewButtons =
  document.getElementById("reviewButtons");


function showAgentStatus(message) {
  if (agentStatus) {
    agentStatus.textContent = message;
  }
}


function showAgentOutput(element, data) {
  if (!element) return;

  element.textContent = JSON.stringify(
    data ?? {},
    null,
    2
  );
}


function setReviewButtonsDisabled(disabled) {
  if (!reviewButtons) return;

  reviewButtons
    .querySelectorAll("[data-decision]")
    .forEach((button) => {
      button.disabled = disabled;
    });
}


async function readAgentResponse(response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error || `Request failed: ${response.status}`
    );
  }

  return data;
}


/* ==========================================
   START MULTI-AGENT WORKFLOW
   ========================================== */

async function runEventMultiAgent() {
  if (agentBusy) return;

  const userRequest = agentRequestInput?.value.trim();

  if (!userRequest) {
    showAgentStatus(
      "Please enter a question about campus events."
    );
    return;
  }

  agentBusy = true;
  currentAgentWorkflowId = null;

  if (runAgentButton) {
    runAgentButton.disabled = true;
    runAgentButton.textContent = "Running AI Agents...";
  }

  if (agentResults) {
    agentResults.hidden = true;
  }

  if (humanReviewStatus) {
    humanReviewStatus.textContent = "";
  }

  if (reviewReason) {
    reviewReason.value = "";
  }

  setReviewButtonsDisabled(true);

  showAgentStatus(
    "Planner, Worker and Reviewer are processing your request. This may take a few minutes."
  );

  try {
    const response = await fetch(
      "/api/multi-agent/event-workflow",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_request: userRequest
        })
      }
    );

    const data = await readAgentResponse(response);

    showAgentOutput(
      plannerOutput,
      data.planner_result
    );

    showAgentOutput(
      workerOutput,
      data.worker_result
    );

    showAgentOutput(
      reviewerOutput,
      data.reviewer_result
    );

    if (agentResults) {
      agentResults.hidden = false;
    }

    if (
      data.status !== "pending_human_review" ||
      !data.workflow_id
    ) {
      showAgentStatus(
        `Workflow status: ${data.status || "unknown"}. Human review is not available.`
      );
      return;
    }

    currentAgentWorkflowId = data.workflow_id;

    setReviewButtonsDisabled(false);

    showAgentStatus(
      "All three agents completed. Please review the results and submit your decision."
    );

  } catch (error) {
    showAgentStatus(
      `Multi-Agent error: ${error.message}`
    );
    console.error("Multi-Agent workflow error:", error);

  } finally {
    agentBusy = false;

    if (runAgentButton) {
      runAgentButton.disabled = false;
      runAgentButton.textContent =
        "✨ Run Multi-Agent Analysis";
    }
  }
}


/* ==========================================
   HUMAN REVIEW DECISION
   ========================================== */

async function submitHumanReview(decision) {
  if (agentBusy || !currentAgentWorkflowId) {
    return;
  }

  const allowed = [
    "Accept",
    "Partially Accept",
    "Reject"
  ];

  if (!allowed.includes(decision)) {
    return;
  }

  const reason = reviewReason?.value.trim() || "";

  if (
    decision !== "Accept" &&
    !reason
  ) {
    if (humanReviewStatus) {
      humanReviewStatus.textContent =
        "Please provide a reason for this decision.";
    }
    return;
  }

  agentBusy = true;
  setReviewButtonsDisabled(true);

  if (runAgentButton) {
    runAgentButton.disabled = true;
  }

  if (humanReviewStatus) {
    humanReviewStatus.textContent =
      "Submitting your review...";
  }

  try {
    const response = await fetch(
      `/api/multi-agent/event-workflow/${encodeURIComponent(
        currentAgentWorkflowId
      )}/decision`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          decision: decision,
          reason: reason
        })
      }
    );

    const data = await readAgentResponse(response);

    if (data.status !== "completed") {
      throw new Error(
        `Unexpected workflow status: ${data.status}`
      );
    }

    if (humanReviewStatus) {
      humanReviewStatus.textContent =
        `Review completed: ${decision}.`;
    }

    showAgentStatus(
      "Multi-Agent workflow and Human Review completed successfully."
    );

    currentAgentWorkflowId = null;

  } catch (error) {
    if (humanReviewStatus) {
      humanReviewStatus.textContent =
        `Review error: ${error.message}`;
    }

    // Allow retry if the decision was not confirmed.
    setReviewButtonsDisabled(true);

    if (currentAgentWorkflowId) {
      setReviewButtonsDisabled(false);
    }

  } finally {
    agentBusy = false;

    if (runAgentButton) {
      runAgentButton.disabled = false;
    }
  }
}


/* ==========================================
   EVENT LISTENERS
   ========================================== */

if (runAgentButton) {
  runAgentButton.addEventListener(
    "click",
    runEventMultiAgent
  );
}

if (reviewButtons) {
  reviewButtons.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest(
        "[data-decision]"
      );

      if (!button || !reviewButtons.contains(button)) {
        return;
      }

      submitHumanReview(
        button.dataset.decision
      );
    }
  );
}

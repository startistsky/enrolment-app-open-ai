const API = "";

let resources = [];
let editId = null;
let aiMode = "ai";
let aiRequestInProgress = false;

const $ = id => document.getElementById(id);

const grid = $("resourceGrid");
const search = $("search");
const typeFilter = $("typeFilter");
const buildingFilter = $("buildingFilter");
const availabilityFilter = $("availabilityFilter");
const chat = $("chat");
const input = $("chatInput");
const messages = $("messages");

// Load campus resources
async function loadResources() {
  try {
    grid.innerHTML = "<p>Loading campus resources...</p>";

    const res = await fetch(`${API}/resources`, {
      cache: "no-store"
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    resources = await res.json();

    updateFilters();
    renderResources();

  } catch (error) {
    console.error("Failed to load resources:", error);

    grid.innerHTML =
      "<p>Unable to load campus resources.</p>";

    $("resultCount").textContent = "0 resources";
  }
}

// Return resource icon
function icon(type) {
  return {
    "Library": "📚",
    "Study Room": "🪑",
    "Computer Lab": "🖥️",
    "Printer": "🖨️",
    "Parking": "🚗"
  }[type] || "🏫";
}

// Update resource filters
function updateFilters() {
  const selectedType = typeFilter.value;
  const selectedBuilding = buildingFilter.value;

  const types = [
    ...new Set(
      resources.map(r => r.resource_type)
    )
  ].sort();

  const buildings = [
    ...new Set(
      resources.map(r => r.building)
    )
  ].sort();

  typeFilter.innerHTML =
    `<option value="">All types</option>` +
    types
      .map(type =>
        `<option value="${type}">${type}</option>`
      )
      .join("");

  buildingFilter.innerHTML =
    `<option value="">All buildings</option>` +
    buildings
      .map(building =>
        `<option value="${building}">${building}</option>`
      )
      .join("");

  typeFilter.value = selectedType;
  buildingFilter.value = selectedBuilding;
}

// Check search text
function matchesSearch(resource, query) {
  if (!query) return true;

  const text = `
    ${resource.resource_name || ""}
    ${resource.resource_type || ""}
    ${resource.building || ""}
    ${resource.location || ""}
    ${resource.description || ""}
  `.toLowerCase();

  return text.includes(query.toLowerCase());
}

// Display resource cards
function renderResources() {
  const query = search.value.trim().toLowerCase();
  const type = typeFilter.value;
  const building = buildingFilter.value;
  const availability = availabilityFilter.value;

  const filtered = resources.filter(resource => {
    return (
      matchesSearch(resource, query) &&
      (!type ||
        resource.resource_type === type) &&
      (!building ||
        resource.building === building) &&
      (!availability ||
        resource.availability_status === availability)
    );
  });

  $("resultCount").textContent =
    `${filtered.length} resource${filtered.length === 1 ? "" : "s"}`;

  grid.innerHTML = filtered.map(resource => `
    <article
      class="card"
      data-id="${resource.resource_id}">

      <div class="image">

        <span class="emoji">
          ${icon(resource.resource_type)}
        </span>

        <span class="tag">
          ${resource.resource_type}
        </span>

        <span class="
          availability-pill
          ${(resource.availability_status || "")
            .toLowerCase()}
        ">
          ${resource.availability_status}
        </span>

      </div>

      <div class="content">

        <h3>
          ${resource.resource_name}
        </h3>

        <p>
          ${resource.description || ""}
        </p>

        <div class="meta">

          <span>
            📍 ${resource.location || resource.building}
          </span>

          <span>
            👥 Capacity:
            ${resource.capacity ?? "N/A"}
          </span>

          <span>
            🕒 ${resource.opening_hours || "N/A"}
          </span>

        </div>

      </div>

    </article>
  `).join("");
}

// Open resource details
function openDetail(id) {
  const resource = resources.find(
    item => item.resource_id === id
  );

  if (!resource) return;

  $("detailContent").innerHTML = `
    <div class="detail-icon">
      ${icon(resource.resource_type)}
    </div>

    <div class="detail-tags">

      <span class="tag-static">
        ${resource.resource_type}
      </span>

      <span class="
        availability-static
        ${(resource.availability_status || "")
          .toLowerCase()}
      ">
        ${resource.availability_status}
      </span>

    </div>

    <h2>
      ${resource.resource_name}
    </h2>

    <p>
      ${resource.description || ""}
    </p>

    <div class="detail-grid">

      <div>
        <strong>Building</strong>
        ${resource.building || "N/A"}
      </div>

      <div>
        <strong>Floor</strong>
        ${resource.floor || "N/A"}
      </div>

      <div>
        <strong>Capacity</strong>
        ${resource.capacity ?? "N/A"}
      </div>

      <div>
        <strong>Hours</strong>
        ${resource.opening_hours || "N/A"}
      </div>

    </div>

    <div class="detail-actions">

      <button
        class="secondary-btn"
        onclick="editResource(${id})">
        Edit
      </button>

      <button
        class="delete-btn"
        onclick="deleteResource(${id})">
        Delete
      </button>

    </div>
  `;

  $("detailModal")?.classList.add("open");
}

// Open add resource form
function openForm() {
  editId = null;

  $("resourceForm")?.reset();

  if ($("resourceFormTitle")) {
    $("resourceFormTitle").textContent =
      "Add Campus Resource";
  }

  if ($("resourceFormSubmitButton")) {
    $("resourceFormSubmitButton").textContent =
      "Add Resource";
  }

  $("resourceFormModal")?.classList.add("open");
}

// Open edit resource form
function editResource(id) {
  const resource = resources.find(
    item => item.resource_id === id
  );

  if (!resource) return;

  editId = id;

  $("formName").value =
    resource.resource_name || "";

  $("formType").value =
    resource.resource_type || "";

  $("formBuilding").value =
    resource.building || "";

  $("formFloor").value =
    resource.floor || "";

  $("formCapacity").value =
    resource.capacity ?? "";

  $("formAvailability").value =
    resource.availability_status || "Available";

  $("formHours").value =
    resource.opening_hours || "";

  $("formLocation").value =
    resource.location || "";

  $("formDescription").value =
    resource.description || "";

  $("resourceFormTitle").textContent =
    "Edit Campus Resource";

  $("resourceFormSubmitButton").textContent =
    "Save Changes";

  $("detailModal")?.classList.remove("open");

  $("resourceFormModal")?.classList.add("open");
}

// Save resource
async function saveResource(event) {
  event.preventDefault();

  const resourceData = {
    resource_name:
      $("formName").value.trim(),

    resource_type:
      $("formType").value,

    building:
      $("formBuilding").value.trim(),

    floor:
      $("formFloor").value.trim(),

    capacity:
      $("formCapacity").value === ""
        ? null
        : Number($("formCapacity").value),

    availability_status:
      $("formAvailability").value,

    opening_hours:
      $("formHours").value.trim(),

    location:
      $("formLocation").value.trim(),

    description:
      $("formDescription").value.trim()
  };

  const url = editId
    ? `${API}/resources/${editId}`
    : `${API}/resources`;

  const method = editId
    ? "PUT"
    : "POST";

  try {
    const res = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(resourceData),
      cache: "no-store"
    });

    if (!res.ok) {
      throw new Error(
        `${method} failed (${res.status})`
      );
    }

    $("resourceFormModal")
      ?.classList.remove("open");

    editId = null;

    await loadResources();

  } catch (error) {
    console.error(
      "Failed to save resource:",
      error
    );

    alert(
      "Unable to save resource."
    );
  }
}

// Delete resource
async function deleteResource(id) {
  const resource = resources.find(
    item => item.resource_id === id
  );

  if (!resource) return;

  const confirmed = confirm(
    `Delete ${resource.resource_name}?`
  );

  if (!confirmed) return;

  try {
    const res = await fetch(
      `${API}/resources/${id}`,
      {
        method: "DELETE",
        cache: "no-store"
      }
    );

    if (!res.ok) {
      throw new Error(
        `DELETE failed (${res.status})`
      );
    }

    $("detailModal")
      ?.classList.remove("open");

    await loadResources();

  } catch (error) {
    console.error(
      "Failed to delete resource:",
      error
    );

    alert(
      "Unable to delete resource."
    );
  }
}

// Open or close AI chat
function toggleChat(open) {
  if (!chat) return;

  const show =
    typeof open === "boolean"
      ? open
      : !chat.classList.contains("open");

  chat.classList.toggle(
    "open",
    show
  );

  // Hide launcher while chat is open
  const launcher =
    $("chatLauncher");

  if (launcher) {
    launcher.classList.toggle(
      "hidden",
      show
    );
  }

  if (show) {
    setTimeout(
      () => input?.focus(),
      200
    );
  }
}

// Add chat message
function addMessage(
  text,
  type = "bot",
  label = ""
) {
  if (!messages) return null;

  const message =
    document.createElement("div");

  message.className =
    `msg ${type}`;

  if (label && type === "bot") {
    const title =
      document.createElement("div");

    title.className =
      "message-label";

    title.textContent =
      label;

    message.appendChild(title);
  }

  const body =
    document.createElement("div");

  body.className =
    "message-text";

  body.textContent =
    text;

  message.appendChild(body);

  messages.appendChild(message);

  messages.scrollTop =
    messages.scrollHeight;

  return body;
}

// Change AI mode
function setMode(mode) {
  aiMode = mode;

  document
    .querySelectorAll("[data-ai-mode]")
    .forEach(button => {

      button.classList.toggle(
        "active",
        button.dataset.aiMode === mode
      );

    });

  const information = {
    ai: [
      "AI Assistant",
      "Natural language campus resource help."
    ],

    rag: [
      "RAG Grounded",
      "Answers grounded in campus resource data."
    ],

    mcp: [
      "MCP Tools",
      "Structured campus resource tools."
    ],

    "multi-agent": [
      "Multi-Agent Review",
      "Agent workflow with human review required."
    ]
  };

  const info =
    information[mode];

  if ($("aiModeInfo")) {
    $("aiModeInfo").innerHTML = `
      <strong>${info[0]}</strong>
      <span>${info[1]}</span>
    `;
  }
}

// Detect questions for other campus modules
function detectOutOfDomain(text) {
  const query = text.toLowerCase();

  const eventWords = [
    "event",
    "events",
    "workshop",
    "workshops",
    "seminar",
    "seminars"
  ];

  if (
    eventWords.some(
      word => query.includes(word)
    )
  ) {
    return "events";
  }

  return null;
}

// Detect MCP request
function detectMcp(text) {
  const query =
    text.toLowerCase();

  if (
    query.includes("count") ||
    query.includes("how many") ||
    query.includes("number of resources")
  ) {
    return {
      tool: "count"
    };
  }

  const types = {
    "Study Room": [
      "study room",
      "study space",
      "book a room",
      "book room",
      "room booking",
      "rooms",
      "room",
      "quiet",
      "study"
    ],

    "Computer Lab": [
      "computer lab",
      "computer",
      "pc"
    ],

    "Printer": [
      "printer",
      "printing",
      "print"
    ],

    "Library": [
      "library",
      "book"
    ],

    "Parking": [
      "parking",
      "park",
      "car"
    ]
  };

  for (
    const [type, words]
    of Object.entries(types)
  ) {
    if (
      words.some(
        word => query.includes(word)
      )
    ) {
      return {
        tool: "type",
        type
      };
    }
  }

  return null;
}

// Ask MCP tool
async function askMcp(question) {
  const request =
    detectMcp(question);

  if (!request) {
    return {
      answer:
        "I can query Study Rooms, " +
        "Computer Labs, Printers, " +
        "Libraries and Parking.",
      data: {
        request: null,
        result: null
      }
    };
  }

  const url =
    request.tool === "count"

      ? `${API}/api/mcp/resource-count`

      : `${API}/api/mcp/resource-by-type/` +
        encodeURIComponent(request.type);

  const res =
    await fetch(url, {
      cache: "no-store"
    });

  if (!res.ok) {
    throw new Error(
      `MCP request failed (${res.status})`
    );
  }

  const data =
    await res.json();

  const result =
    data.result || {};

  if (request.tool === "count") {
    return {
      answer:
        `There are ` +
        `${result.resource_count ?? 0} ` +
        `campus resources.`,
      data: {
        request,
        response: data,
        result
      }
    };
  }

  const found =
    result.resources || [];

  if (!found.length) {
    return {
      answer:
        `No ${request.type.toLowerCase()} ` +
        `resources were found.`,
      data: {
        request,
        response: data,
        result
      }
    };
  }

  const names =
    found
      .map(
        resource =>
          `• ${resource.resource_name}`
      )
      .join("\n");

  return {
    answer:
      `I found ${found.length} ` +
      `${request.type.toLowerCase()} ` +
      `resource${found.length === 1 ? "" : "s"}:\n` +
      names,
    data: {
      request,
      response: data,
      result
    }
  };
}

// Ask normal AI
async function askAi(question) {
  const res =
    await fetch(
      `${API}/recommend`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          question
        }),

        cache: "no-store"
      }
    );

  const data =
    await res.json()
      .catch(() => ({}));

  if (!res.ok) {
    throw new Error(
      data.error ||
      `AI request failed (${res.status})`
    );
  }

  return {
    answer:
      data.recommendation ||
      data.answer ||
      "No recommendation was returned.",
    data
  };
}

// Ask RAG
async function askRag(question) {
  const res =
    await fetch(
      `${API}/rag/recommend`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          question
        }),

        cache: "no-store"
      }
    );

  const data =
    await res.json()
      .catch(() => ({}));

  if (!res.ok) {
    throw new Error(
      data.error ||
      `RAG request failed (${res.status})`
    );
  }

  return {
    answer:
      data.answer ||
      data.recommendation ||
      "No grounded answer was returned.",
    data
  };
}

// Ask the Multi-Agent resource workflow
async function askMultiAgent(question) {
  const res = await fetch(
    `${API}/api/multi-agent/resource`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question }),
      cache: "no-store"
    }
  );

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(
      data.error || `Multi-Agent request failed (${res.status})`
    );
  }

  return {
    answer: data.answer || data.summary ||
      "Multi-Agent workflow completed its initial review.",
    data
  };
}

// Display AI, RAG or MCP response
function renderModeResponse(messageBody, mode, response) {
  if (!messageBody) return;

  const data = response.data || {};

  // Multi-Agent workflow and human review evidence
  if (mode === "multi-agent") {
    messageBody.textContent =
      data.worker_result?.answer || response.answer;

    const card = document.createElement("div");
    card.className = "response-meta multi-agent-meta";

    const heading = document.createElement("div");
    heading.className = "response-meta-heading";
    heading.textContent = "🤖 MULTI-AGENT WORKFLOW";
    card.appendChild(heading);

    function addField(label, value) {
      const block = document.createElement("div");
      block.className = "response-meta-block";

      const name = document.createElement("span");
      name.className = "response-meta-label";
      name.textContent = label;

      const content = document.createElement("span");
      content.className = "response-meta-value";
      content.textContent = String(value ?? "Not returned");

      block.appendChild(name);
      block.appendChild(content);
      card.appendChild(block);
      return content;
    }

    addField("WORKFLOW ID", data.workflow_id);
    const statusText = addField("STATUS", data.status);

    addField("PLANNER STATUS", data.planner_status);
    addField("PLANNER PLAN", data.planner_result?.plan);

    addField("WORKER STATUS", data.worker_status);
    addField("WORKER ANSWER", data.worker_result?.answer);

    addField("REVIEWER STATUS", data.reviewer_status);
    addField("REVIEWER RISK", data.reviewer_result?.risk);
    addField("REVIEWER RECOMMENDATION",
      data.reviewer_result?.recommendation);

    const reviewText = addField(
      "HUMAN REVIEW",
      data.human_review?.status || "Not returned"
    );

    if (
      data.workflow_id &&
      data.status === "pending_human_review"
    ) {
      const actions = document.createElement("div");
      actions.className = "multi-agent-actions";

      const reason = document.createElement("input");
      reason.type = "text";
      reason.placeholder = "Review reason (optional)";
      reason.className = "multi-agent-reason";
      actions.appendChild(reason);

      const buttons = document.createElement("div");
      buttons.className = "multi-agent-buttons";

      for (const decision of [
        "Accept", "Partially Accept", "Reject"
      ]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = decision;

        button.addEventListener("click", async () => {
          const allButtons = buttons.querySelectorAll("button");
          allButtons.forEach(item => item.disabled = true);

          try {
            const res = await fetch(
              `${API}/api/multi-agent/${encodeURIComponent(
                data.workflow_id
              )}/decision`,
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json"
                },
                body: JSON.stringify({
                  decision,
                  reason: reason.value.trim()
                })
              }
            );

            const result = await res.json();

            if (!res.ok) {
              throw new Error(
                result.error || "Human review failed"
              );
            }

            statusText.textContent = result.status;
            reviewText.textContent =
              `${result.human_review?.status}: ${decision}`;

            // Update the saved Agent Trace after human review
            const saved = localStorage.getItem(
              "student3AgentTrace"
            );

            if (saved) {
              try {
                const trace = JSON.parse(saved);

                if (trace.workflow_id === data.workflow_id) {
                  trace.status = result.status;
                  trace.human_review = result.human_review;
                  trace.adapt =
                    `Human decision: ${decision}. ` +
                    `Reason: ${result.human_review?.reason || "Not provided"}.`;

                  const statusDetail = trace.details?.find(
                    item => item.label === "WORKFLOW STATUS"
                  );

                  if (statusDetail) {
                    statusDetail.value = result.status;
                  }

                  const reviewDetail = trace.details?.find(
                    item => item.label === "HUMAN REVIEW"
                  );

                  if (reviewDetail) {
                    reviewDetail.value =
                      `${result.human_review?.status}: ${decision}`;
                  }

                  localStorage.setItem(
                    "student3AgentTrace",
                    JSON.stringify(trace)
                  );
                }
              } catch (error) {
                console.warn("Could not update Agent Trace:", error);
              }
            }

            actions.remove();

          } catch (error) {
            reviewText.textContent = error.message;
            allButtons.forEach(item => item.disabled = false);
          }
        });

        buttons.appendChild(button);
      }

      actions.appendChild(buttons);
      card.appendChild(actions);
    }

    messageBody.appendChild(card);
    return;
  }

  // AI stays conversational and simple
  if (mode === "ai") {
    messageBody.textContent =
      response.answer;

    return;
  }

  // RAG shows grounded knowledge evidence
  if (mode === "rag") {
    messageBody.textContent =
      response.answer;

    const citations =
      data.citations || [];

    const matches =
      data.matches || [];

    const source =
      citations.length
        ? citations[0]
        : "No citation returned";

    const card =
      document.createElement("div");

    card.className =
      "response-meta rag-meta";

    const heading =
      document.createElement("div");

    heading.className =
      "response-meta-heading";

    heading.textContent =
      "◈  GROUNDING EVIDENCE";

    card.appendChild(heading);

    const sourceBlock =
      document.createElement("div");

    sourceBlock.className =
      "response-meta-block";

    const sourceLabel =
      document.createElement("span");

    sourceLabel.className =
      "response-meta-label";

    sourceLabel.textContent =
      "SOURCE";

    const sourceValue =
      document.createElement("span");

    sourceValue.className =
      "response-meta-value";

    sourceValue.textContent =
      source;

    sourceBlock.appendChild(sourceLabel);
    sourceBlock.appendChild(sourceValue);
    card.appendChild(sourceBlock);

    const stats =
      document.createElement("div");

    stats.className =
      "response-meta-grid";

    const confidence =
      document.createElement("div");

    const confidenceLabel =
      document.createElement("span");

    confidenceLabel.className =
      "response-meta-label";

    confidenceLabel.textContent =
      "CONFIDENCE";

    const confidenceValue =
      document.createElement("span");

    confidenceValue.className =
      "response-meta-value";

    confidenceValue.textContent =
      (data.confidence || "unknown")
        .toUpperCase();

    confidence.appendChild(
      confidenceLabel
    );

    confidence.appendChild(
      confidenceValue
    );

    const retrieved =
      document.createElement("div");

    const retrievedLabel =
      document.createElement("span");

    retrievedLabel.className =
      "response-meta-label";

    retrievedLabel.textContent =
      "RETRIEVED";

    const retrievedValue =
      document.createElement("span");

    retrievedValue.className =
      "response-meta-value";

    retrievedValue.textContent =
      `${matches.length} matches`;

    retrieved.appendChild(
      retrievedLabel
    );

    retrieved.appendChild(
      retrievedValue
    );

    stats.appendChild(confidence);
    stats.appendChild(retrieved);

    card.appendChild(stats);
    messageBody.appendChild(card);

    return;
  }

  // MCP shows structured tool execution
  if (mode === "mcp") {
    messageBody.textContent =
      response.answer;

    const request =
      data.request;

    const result =
      data.result || {};

    let toolName =
      "No tool matched";

    let input =
      "N/A";

    let returned =
      "No structured result";

    if (request?.tool === "count") {
      toolName =
        "resource_count";

      input =
        "All campus resources";

      returned =
        `${result.resource_count ?? 0} resources`;
    }

    if (request?.tool === "type") {
      toolName =
        "resource_by_type";

      input =
        request.type || "N/A";

      returned =
        `${(result.resources || []).length} resources`;
    }

    const card =
      document.createElement("div");

    card.className =
      "response-meta mcp-meta";

    const heading =
      document.createElement("div");

    heading.className =
      "response-meta-heading";

    heading.textContent =
      "⚙  TOOL EXECUTION";

    card.appendChild(heading);

    const toolBlock =
      document.createElement("div");

    toolBlock.className =
      "response-meta-block";

    const toolLabel =
      document.createElement("span");

    toolLabel.className =
      "response-meta-label";

    toolLabel.textContent =
      "TOOL";

    const toolValue =
      document.createElement("span");

    toolValue.className =
      "response-meta-value";

    toolValue.textContent =
      toolName;

    toolBlock.appendChild(toolLabel);
    toolBlock.appendChild(toolValue);
    card.appendChild(toolBlock);

    const stats =
      document.createElement("div");

    stats.className =
      "response-meta-grid";

    const inputBlock =
      document.createElement("div");

    const inputLabel =
      document.createElement("span");

    inputLabel.className =
      "response-meta-label";

    inputLabel.textContent =
      "INPUT";

    const inputValue =
      document.createElement("span");

    inputValue.className =
      "response-meta-value";

    inputValue.textContent =
      input;

    inputBlock.appendChild(inputLabel);
    inputBlock.appendChild(inputValue);

    const returnedBlock =
      document.createElement("div");

    const returnedLabel =
      document.createElement("span");

    returnedLabel.className =
      "response-meta-label";

    returnedLabel.textContent =
      "RETURNED";

    const returnedValue =
      document.createElement("span");

    returnedValue.className =
      "response-meta-value";

    returnedValue.textContent =
      returned;

    returnedBlock.appendChild(
      returnedLabel
    );

    returnedBlock.appendChild(
      returnedValue
    );

    stats.appendChild(inputBlock);
    stats.appendChild(returnedBlock);

    card.appendChild(stats);
    messageBody.appendChild(card);
  }
}


// Add Agent Trace link below an AI response
function addTraceLink(messageBody) {
  if (!messageBody) return;

  const message =
    messageBody.closest(".msg");

  if (!message) return;

  const traceLink =
    document.createElement("a");

  traceLink.className =
    "agent-trace-link";

  traceLink.href =
    "agent-trace.html";

  traceLink.target =
    "_blank";

  traceLink.rel =
    "noopener";

  traceLink.textContent =
    "View Agent Trace →";

  message.appendChild(traceLink);

  messages.scrollTop =
    messages.scrollHeight;
}

// Save runtime agent trace
function saveAgentTrace(question, mode, response) {
  const data = response.data || {};

  const trace = {
    timestamp: new Date().toISOString(),
    question,
    mode,
    details: [],
    plan: "",
    act: "",
    observe: "",
    adapt: "",
    result: response.answer
  };

  if (mode === "mcp") {
    const request = data.request;
    const result = data.result || {};
    const found = result.resources || [];

    let tool = "No tool matched";
    let input = "N/A";
    let returned = "No structured result";

    if (request?.tool === "count") {
      tool = "resource_count";
      input = "All campus resources";
      returned = `${result.resource_count ?? 0} resources`;
    }

    if (request?.tool === "type") {
      tool = "resource_by_type";
      input = request.type || "N/A";
      returned = `${found.length} resources`;
    }

    trace.details = [
      {
        label: "TOOL",
        value: tool
      },
      {
        label: "INPUT",
        value: input
      },
      {
        label: "RETURNED",
        value: returned
      }
    ];

    trace.plan =
      request
        ? `Use MCP structured resource tool for ${request.type || "resource count"}.`
        : "Check whether the question maps to an available MCP resource tool.";

    trace.act =
      request?.tool === "count"
        ? "Called MCP tool: resource_count."
        : request?.type
        ? `Called MCP tool: resource_by_type with type ${request.type}.`
        : "No matching MCP tool was called.";

    trace.observe =
      request?.tool === "count"
        ? `MCP returned ${result.resource_count ?? 0} campus resources.`
        : request?.type
        ? `MCP returned ${found.length} ${request.type} resource result(s).`
        : "No structured MCP result was available.";

    trace.adapt =
      "Converted the structured MCP result into a user-readable response.";
  }

  if (mode === "rag") {
    const matches = data.matches || [];
    const citations = data.citations || [];

    trace.details = [
      {
        label: "CONFIDENCE",
        value: (data.confidence || "unknown").toUpperCase()
      },
      {
        label: "RETRIEVED",
        value: `${matches.length} matches`
      },
      {
        label: "CITATIONS",
        value: String(citations.length)
      }
    ];

    trace.plan =
      "Retrieve relevant campus resource knowledge before generating the answer.";

    trace.act =
      `Called the RAG recommendation service and retrieved ${matches.length} match(es).`;

    trace.observe =
      `Grounding confidence: ${data.confidence || "unknown"}. ` +
      `Citations returned: ${citations.length}.`;

    trace.adapt =
      "Generated the final answer using the retrieved grounded context.";
  }

  if (mode === "ai") {
    const candidates =
      data.candidate_resources || [];

    const requested =
      data.requested_resource_types || [];

    trace.details = [
      {
        label: "MODEL",
        value: data.model || "Configured model"
      },
      {
        label: "CANDIDATES",
        value: String(
          data.candidate_count ?? candidates.length
        )
      },
      {
        label: "RESOURCE TYPE",
        value: requested.length
          ? requested.join(", ")
          : "General"
      }
    ];

    trace.plan =
      requested.length
        ? `Identify relevant ${requested.join(", ")} campus resources.`
        : "Identify relevant campus resources for the user's request.";

    trace.act =
      `Called the AI recommendation service using ${data.model || "the configured model"}.`;

    trace.observe =
      `${data.candidate_count ?? candidates.length} candidate resource(s) were selected.`;

    trace.adapt =
      "Generated a concise recommendation from the selected campus resource context.";
  }

  if (mode === "multi-agent") {
    const planner = data.planner_result || {};
    const worker = data.worker_result || {};
    const reviewer = data.reviewer_result || {};
    const review = data.human_review || {};

    trace.workflow_id = data.workflow_id || "";
    trace.status = data.status || "";
    trace.human_review = review;

    trace.details = [
      {
        label: "WORKFLOW ID",
        value: trace.workflow_id
      },
      {
        label: "WORKFLOW STATUS",
        value: trace.status
      },
      {
        label: "PLANNER",
        value: data.planner_status || "unknown"
      },
      {
        label: "WORKER",
        value: data.worker_status || "unknown"
      },
      {
        label: "REVIEWER",
        value: data.reviewer_status || "unknown"
      },
      {
        label: "HUMAN REVIEW",
        value: review.status || "unknown"
      }
    ];

    trace.plan =
      planner.plan || "Planner output not available.";

    trace.act =
      worker.answer || "Worker output not available.";

    trace.observe =
      [
        reviewer.risk,
        reviewer.recommendation
      ].filter(Boolean).join("\\n\\n") ||
      "Reviewer output not available.";

    trace.adapt =
      review.status === "completed"
        ? `Human decision: ${review.decision || "unknown"}. ` +
          `Reason: ${review.reason || "Not provided"}.`
        : "Awaiting human review decision.";

    trace.result =
      worker.answer || response.answer;
  }

  localStorage.setItem(
    "student3AgentTrace",
    JSON.stringify(trace)
  );
}


// Send chat message
async function sendMessage() {
  if (
    aiRequestInProgress ||
    !input
  ) {
    return;
  }

  const question =
    input.value.trim();

  if (!question) return;

  const outOfDomain =
    detectOutOfDomain(question);

  if (outOfDomain === "events") {
    addMessage(
      question,
      "user"
    );

    input.value = "";

    addMessage(
      "This question belongs to Campus Events. " +
      "Please use the Events section for event information.",
      "bot",
      "Campus AI"
    );

    return;
  }

  addMessage(
    question,
    "user"
  );

  input.value = "";

  aiRequestInProgress = true;

  if ($("chatSendButton")) {
    $("chatSendButton").disabled = true;
  }

  // Keep the selected mode for this request
  const requestMode = aiMode;

  const label =
    requestMode === "multi-agent"
      ? "Multi-Agent Review"
      : requestMode === "mcp"
      ? "MCP Tool Result"
      : requestMode === "rag"
      ? "RAG Grounded Answer"
      : "Campus AI";

  const loading =
    addMessage(
      "Checking campus resources...",
      "bot",
      label
    );

  try {
    let response;

    if (requestMode === "mcp") {
      response =
        await askMcp(question);

    } else if (requestMode === "rag") {
      response =
        await askRag(question);

    } else if (requestMode === "multi-agent") {
      response =
        await askMultiAgent(question);

    } else {
      response =
        await askAi(question);
    }

    saveAgentTrace(
      question,
      requestMode,
      response
    );

    if (loading) {
      renderModeResponse(
        loading,
        requestMode,
        response
      );

      addTraceLink(loading);
    }

  } catch (error) {
    console.error(
      "Chat request failed:",
      error
    );

    if (loading) {
      loading.textContent =
        "I could not reach this service. " +
        "Please check that the required services are running.";
    }

  } finally {
    aiRequestInProgress = false;

    if ($("chatSendButton")) {
      $("chatSendButton").disabled = false;
    }

    input?.focus();
  }
}

// Open add resource button
$("addResourceButton")
  ?.addEventListener(
    "click",
    openForm
  );

// Open AI button
$("askAiButton")
  ?.addEventListener(
    "click",
    () => toggleChat(true)
  );

// Toggle floating chat button
$("chatLauncher")
  ?.addEventListener(
    "click",
    () => toggleChat()
  );

// Close chat button
$("chatCloseButton")
  ?.addEventListener(
    "click",
    () => toggleChat(false)
  );

// Close detail modal
$("detailCloseButton")
  ?.addEventListener(
    "click",
    () =>
      $("detailModal")
        ?.classList.remove("open")
  );

// Close resource form button
$("resourceFormCloseButton")
  ?.addEventListener(
    "click",
    () =>
      $("resourceFormModal")
        ?.classList.remove("open")
  );

// Cancel resource form button
$("resourceFormCancelButton")
  ?.addEventListener(
    "click",
    () =>
      $("resourceFormModal")
        ?.classList.remove("open")
  );

// Submit resource form
$("resourceForm")
  ?.addEventListener(
    "submit",
    saveResource
  );

// Send chat button
$("chatSendButton")
  ?.addEventListener(
    "click",
    sendMessage
  );

// Send chat with Enter
input?.addEventListener(
  "keydown",
  event => {

    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }

  }
);

// Change AI mode
document
  .querySelectorAll("[data-ai-mode]")
  .forEach(button => {

    button.addEventListener(
      "click",
      () =>
        setMode(
          button.dataset.aiMode
        )
    );

  });

// Use quick questions
document
  .querySelectorAll("[data-quick]")
  .forEach(button => {

    button.addEventListener(
      "click",
      () => {

        toggleChat(true);

        input.value =
          button.dataset.quick;

        sendMessage();
      }
    );

  });

// Open clicked resource
grid?.addEventListener(
  "click",
  event => {

    const card =
      event.target.closest("[data-id]");

    if (!card) return;

    openDetail(
      Number(card.dataset.id)
    );

  }
);

// Update resource filters
[
  search,
  typeFilter,
  buildingFilter,
  availabilityFilter
]
  .filter(Boolean)
  .forEach(element => {

    element.addEventListener(
      "input",
      renderResources
    );

  });

// Close chat when clicking outside
document.addEventListener(
  "click",
  event => {

    if (!chat) return;

    const open =
      chat.classList.contains("open");

    const inside =
      chat.contains(event.target);

    const launcher =
      event.target.closest("#chatLauncher");

    const askButton =
      event.target.closest("#askAiButton");

    if (
      open &&
      !inside &&
      !launcher &&
      !askButton
    ) {
      toggleChat(false);
    }

  }
);

// Make resource actions available
window.editResource =
  editResource;

window.deleteResource =
  deleteResource;

// Start Student 3 page
loadResources();

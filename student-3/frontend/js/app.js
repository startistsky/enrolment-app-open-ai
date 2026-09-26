const API = `${location.protocol}//${location.hostname}:8003`;

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
    return (
      "I can query Study Rooms, " +
      "Computer Labs, Printers, " +
      "Libraries and Parking."
    );
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
    return (
      `There are ` +
      `${result.resource_count ?? 0} ` +
      `campus resources.`
    );
  }

  const found =
    result.resources || [];

  if (!found.length) {
    return (
      `No ${request.type.toLowerCase()} ` +
      `resources were found.`
    );
  }

  const names =
    found
      .map(
        resource =>
          `• ${resource.resource_name}`
      )
      .join("\n");

  return (
    `I found ${found.length} ` +
    `${request.type.toLowerCase()} ` +
    `resource${found.length === 1 ? "" : "s"}:\n` +
    names
  );
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

  return (
    data.recommendation ||
    data.answer ||
    "No recommendation was returned."
  );
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

  return (
    data.answer ||
    data.recommendation ||
    "No grounded answer was returned."
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

  addMessage(
    question,
    "user"
  );

  input.value = "";

  aiRequestInProgress = true;

  if ($("chatSendButton")) {
    $("chatSendButton").disabled = true;
  }

  const label =
    aiMode === "mcp"
      ? "MCP Tool Result"
      : aiMode === "rag"
      ? "RAG Answer"
      : "Campus AI";

  const loading =
    addMessage(
      "Checking campus resources...",
      "bot",
      label
    );

  try {
    let answer = "";

    if (aiMode === "mcp") {
      answer =
        await askMcp(question);

    } else if (aiMode === "rag") {
      answer =
        await askRag(question);

    } else {
      answer =
        await askAi(question);
    }

    if (loading) {
      loading.textContent =
        answer;
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
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
const adminCategory = document.getElementById("adminCategory");
const adminDate = document.getElementById("adminDate");

let currentMode = "guest";

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

    seedAdminFilters();

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

  const diffDays = Math.floor((d - today) / 86400000);

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
  const q = search.value.trim().toLowerCase();

  const filtered = events.filter((e) => {
    const text =
      `${e.title} ${e.category} ${e.location} ${e.description}`.toLowerCase();

    return !q || text.includes(q);
  });

  count.textContent = `${filtered.length} event${
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

  /*
    The AI chat belongs to the public/guest
    experience, so close it when entering Admin.
  */
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
   ADMIN FILTER OPTIONS
   ========================= */

function seedAdminFilters() {
  if (!adminCategory) return;

  /*
    Prevent duplicate options if loadEvents()
    is called again later.
  */
  adminCategory.innerHTML = '<option value="">All categories</option>';

  const categories = [
    ...new Set(events.map((e) => e.category).filter(Boolean)),
  ].sort();

  categories.forEach((value) => {
    const option = document.createElement("option");

    option.value = value;
    option.textContent = value;

    adminCategory.appendChild(option);
  });
}

/* =========================
   ADMIN VIEW
   ========================= */

function renderAdmin() {
  if (!adminEventTable) return;

  const q = adminSearch.value.trim().toLowerCase();

  const category = adminCategory.value;

  const dateMode = adminDate.value;

  const filtered = events.filter((e) => {
    const text =
      `${e.title} ${e.category} ${e.location} ${e.description}`.toLowerCase();

    const matchesSearch = !q || text.includes(q);

    const matchesCategory = !category || e.category === category;

    const matchesDate = withinRange(e.date, dateMode);

    return matchesSearch && matchesCategory && matchesDate;
  });

  adminCount.textContent = `${filtered.length} event${
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
   ADMIN BUTTON PLACEHOLDERS
   ========================= */

/*
  We have not connected Update and Delete
  to the Flask API yet.

  These functions are placeholders so that
  the buttons do not cause JavaScript errors.
*/

function editEvent(id) {
  const eventItem = events.find((e) => e.id === id);

  if (!eventItem) return;

  console.log("Edit event:", eventItem);

  alert(`Edit "${eventItem.title}" will be implemented in the next step.`);
}

function deleteEvent(id) {
  const eventItem = events.find((e) => e.id === id);

  if (!eventItem) return;

  console.log("Delete event:", eventItem);

  alert(`Delete "${eventItem.title}" will be implemented in the next step.`);
}

/* =========================
   CHAT
   ========================= */

function toggleChat(force) {
  const chat = document.getElementById("chat");

  if (!chat) return;

  const open =
    typeof force === "boolean" ? force : !chat.classList.contains("open");

  chat.classList.toggle("open", open);

  if (open) {
    setTimeout(() => {
      const chatInput = document.getElementById("chatInput");

      if (chatInput) {
        chatInput.focus();
      }
    }, 100);
  }
}

function addMessage(text, type) {
  const messages = document.getElementById("messages");

  const div = document.createElement("div");

  div.className = `msg ${type}`;

  div.textContent = text;

  messages.appendChild(div);

  messages.scrollTop = messages.scrollHeight;
}

function localAiAnswer(question) {
  const q = question.toLowerCase();

  let matches = [];

  if (q.includes("this week") || q.includes("week")) {
    matches = events.filter((e) => withinRange(e.date, "week"));
  } else if (q.includes("career")) {
    matches = events.filter((e) => e.category === "Career");
  } else if (q.includes("building 11")) {
    matches = events.filter((e) => e.location === "Building 11");
  } else if (q.includes("sport") || q.includes("basketball")) {
    matches = events.filter((e) => e.category === "Sport");
  } else if (q.includes("wellbeing") || q.includes("yoga")) {
    matches = events.filter((e) => e.category === "Wellbeing");
  }

  if (matches.length) {
    const sample = matches
      .slice(0, 5)
      .map((e) => `${e.title} (${prettyDate(e.date)}, ${e.location})`)
      .join("; ");

    return `I found ${matches.length} relevant event${
      matches.length === 1 ? "" : "s"
    }: ${sample}${matches.length > 5 ? "…" : ""}`;
  }

  return "I can help with questions about dates, categories and locations. In the real project, this box would send your question together with the event data to Ollama.";
}

function sendMessage() {
  const input = document.getElementById("chatInput");

  const text = input.value.trim();

  if (!text) return;

  addMessage(text, "user");

  input.value = "";

  setTimeout(() => addMessage(localAiAnswer(text), "bot"), 350);
}

function askQuick(text) {
  toggleChat(true);

  document.getElementById("chatInput").value = text;

  sendMessage();
}

function openEventModal() {
  const modal = document.getElementById("eventModal");

  if (!modal) return;

  modal.classList.add("open");

  document.body.style.overflow = "hidden";
}

function closeEventModal() {
  const modal = document.getElementById("eventModal");

  if (!modal) return;

  modal.classList.remove("open");

  document.body.style.overflow = "";

  const form = document.getElementById("eventForm");

  if (form) {
    form.reset();
  }
}

async function createEvent(event) {
  event.preventDefault();

  const title = document.getElementById("eventTitle").value.trim();

  const category = document.getElementById("eventCategory").value.trim();

  const date = document.getElementById("eventDate").value;

  const location = document.getElementById("eventLocation").value.trim();

  const description = document.getElementById("eventDescription").value.trim();

  if (!title || !category || !date || !location || !description) {
    alert("Please complete all required fields.");
    return;
  }

  const newEvent = {
    title,
    category,
    date,
    location,
    description,
  };

  try {
    const response = await fetch("/api/events", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(newEvent),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Failed to create event.");
    }

    closeEventModal();

    await loadEvents();

    renderAdmin();
  } catch (error) {
    console.error("Create event error:", error);

    alert(error.message || "Unable to create the event.");
  }
}

/* =========================
   EVENT LISTENERS
   ========================= */

const eventForm =
  document.getElementById("eventForm");

if (eventForm) {
  eventForm.addEventListener(
    "submit",
    createEvent,
  );
}

/* Guest search */
search.addEventListener("input", render);

/* Admin search */
if (adminSearch) {
  adminSearch.addEventListener("input", renderAdmin);
}

/* Admin category filter */
if (adminCategory) {
  adminCategory.addEventListener("change", renderAdmin);
}

/* Admin date filter */
if (adminDate) {
  adminDate.addEventListener("change", renderAdmin);
}

/* =========================
   INITIAL LOAD
   ========================= */

loadEvents();

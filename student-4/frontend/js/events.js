let events = [];

const grid = document.getElementById("eventGrid");
const search = document.getElementById("search");
const count = document.getElementById("count");


async function loadEvents() {
  const response = await fetch("/api/events");

  events = await response.json();

  render();
}


function prettyDate(value) {
  const d = new Date(value + "T00:00:00");

  return d
    .toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
    })
    .toUpperCase();
}


function withinRange(eventDate, mode) {
  if (!mode) return true;

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


function render() {
  const q = search.value.trim().toLowerCase();

  const filtered = events.filter((e) => {
    const text =
      `${e.title} ${e.category} ${e.location} ${e.description}`.toLowerCase();

    return !q || text.includes(q);
  });

  count.textContent =
    `${filtered.length} event${filtered.length === 1 ? "" : "s"}`;

  grid.innerHTML = filtered
    .map(
      (e) => `
        <article class="card">
          <div class="image">
            <span class="emoji">${e.emoji}</span>
            <span class="tag">${e.category}</span>
            <span class="date-pill">${prettyDate(e.date)}</span>
          </div>

          <div class="content">
            <h3>${e.title}</h3>

            <p>${e.description}</p>

            <div class="meta">
              <span>📍 ${e.location}</span>

              <span>
                📅 ${new Date(e.date + "T00:00:00").toLocaleDateString(
                  "en-AU",
                  {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  },
                )}
              </span>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}


function toggleChat(force) {
  const chat = document.getElementById("chat");

  const open =
    typeof force === "boolean"
      ? force
      : !chat.classList.contains("open");

  chat.classList.toggle("open", open);

  if (open) {
    setTimeout(
      () => document.getElementById("chatInput").focus(),
      100,
    );
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
    matches = events.filter((e) =>
      withinRange(e.date, "week"),
    );
  }

  else if (q.includes("career")) {
    matches = events.filter(
      (e) => e.category === "Career",
    );
  }

  else if (q.includes("building 11")) {
    matches = events.filter(
      (e) => e.location === "Building 11",
    );
  }

  else if (
    q.includes("sport") ||
    q.includes("basketball")
  ) {
    matches = events.filter(
      (e) => e.category === "Sport",
    );
  }

  else if (
    q.includes("wellbeing") ||
    q.includes("yoga")
  ) {
    matches = events.filter(
      (e) => e.category === "Wellbeing",
    );
  }

  if (matches.length) {
    const sample = matches
      .slice(0, 5)
      .map(
        (e) =>
          `${e.title} (${prettyDate(e.date)}, ${e.location})`,
      )
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

  setTimeout(
    () => addMessage(localAiAnswer(text), "bot"),
    350,
  );
}


function askQuick(text) {
  toggleChat(true);

  document.getElementById("chatInput").value = text;

  sendMessage();
}


/* Search events whenever the user types */
search.addEventListener("input", render);


/* Initial load */
loadEvents();
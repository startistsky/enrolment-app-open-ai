const API_BASE = window.ASSIGNMENT_API_URL || "/api";
let assignments = [];

const $ = (selector) => document.querySelector(selector);
const grid = $("#assignmentGrid");
const modal = $("#assignmentModal");

function escapeHtml(value = "") {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}

function showNotice(message, isError = false) {
  const notice = $("#notice");
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
  window.setTimeout(() => { notice.hidden = true; }, 3500);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Request failed");
  return body;
}

function daysUntil(dateValue) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const due = new Date(`${dateValue}T00:00:00`);
  return Math.ceil((due - today) / 86400000);
}

function dueLabel(item) {
  if (item.status === "Completed") return "Completed";
  const days = daysUntil(item.due_date);
  if (days < 0) return `${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"} overdue`;
  if (days === 0) return "Due today";
  return `Due in ${days} day${days === 1 ? "" : "s"}`;
}

function renderSummary() {
  const activeUpcoming = assignments.filter((item) => item.status !== "Completed" && daysUntil(item.due_date) >= 0 && daysUntil(item.due_date) <= 7);
  const average = assignments.length ? Math.round(assignments.reduce((sum, item) => sum + Number(item.progress), 0) / assignments.length) : 0;
  $("#totalCount").textContent = assignments.length;
  $("#upcomingCount").textContent = activeUpcoming.length;
  $("#inProgressCount").textContent = assignments.filter((item) => item.status === "In Progress").length;
  $("#averageProgress").textContent = `${average}%`;
}

function renderAssignments() {
  grid.innerHTML = assignments.map((item) => {
    const overdue = item.status !== "Completed" && daysUntil(item.due_date) < 0;
    return `<article class="assignment-card">
      <div class="card-top"><span class="priority ${item.priority.toLowerCase()}">${escapeHtml(item.priority)} priority</span><button class="menu-button" aria-label="Assignment actions" onclick="editAssignment(${item.assignment_id})">Edit</button></div>
      <p class="subject">${escapeHtml(item.subject_name)}</p><h3>${escapeHtml(item.assignment_title)}</h3>
      <p class="description">${escapeHtml(item.description || "No description provided.")}</p>
      <div class="meta"><span class="${overdue ? "overdue" : ""}">◷ ${escapeHtml(dueLabel(item))}</span><span>${escapeHtml(item.status)}</span></div>
      <div class="progress-row"><span>Progress</span><strong>${item.progress}%</strong></div>
      <div class="progress-track"><span style="width:${item.progress}%"></span></div>
      <div class="card-actions"><button onclick="editAssignment(${item.assignment_id})">Update</button><button class="danger" onclick="deleteAssignment(${item.assignment_id})">Delete</button></div>
    </article>`;
  }).join("");
  $("#emptyState").hidden = assignments.length !== 0;
  renderSummary();
}

async function loadAssignments() {
  const params = new URLSearchParams();
  if ($("#studentFilter").value.trim()) params.set("student_id", $("#studentFilter").value.trim());
  if ($("#statusFilter").value) params.set("status", $("#statusFilter").value);
  if ($("#priorityFilter").value) params.set("priority", $("#priorityFilter").value);
  params.set("sort", $("#sortFilter").value);
  try {
    assignments = await api(`/assignments?${params}`);
    renderAssignments();
  } catch (error) {
    showNotice(`${error.message}. Start the Student 2 services and try again.`, true);
  }
}

function openAssignmentForm(item = null) {
  $("#formTitle").textContent = item ? "Edit assignment" : "New assignment";
  $("#assignmentId").value = item?.assignment_id || "";
  $("#studentId").value = item?.student_id || $("#studentFilter").value || "25220967";
  $("#subjectName").value = item?.subject_name || "";
  $("#assignmentTitle").value = item?.assignment_title || "";
  $("#description").value = item?.description || "";
  $("#dueDate").value = item?.due_date || "";
  $("#priority").value = item?.priority || "Medium";
  $("#status").value = item?.status || "Not Started";
  $("#progress").value = item?.progress ?? 0;
  modal.hidden = false;
}

window.editAssignment = (id) => openAssignmentForm(assignments.find((item) => item.assignment_id === id));
window.deleteAssignment = async (id) => {
  if (!window.confirm("Delete this assignment? This action cannot be undone.")) return;
  try { await api(`/assignments/${id}`, { method: "DELETE" }); showNotice("Assignment deleted."); await loadAssignments(); }
  catch (error) { showNotice(error.message, true); }
};

$("#assignmentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("#assignmentId").value;
  const payload = {
    student_id: $("#studentId").value.trim(), subject_name: $("#subjectName").value.trim(),
    assignment_title: $("#assignmentTitle").value.trim(), description: $("#description").value.trim(),
    due_date: $("#dueDate").value, priority: $("#priority").value, status: $("#status").value,
    progress: Number($("#progress").value),
  };
  try {
    await api(id ? `/assignments/${id}` : "/assignments", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    modal.hidden = true; showNotice(id ? "Assignment updated." : "Assignment created."); await loadAssignments();
  } catch (error) { showNotice(error.message, true); }
});

$("#generateAiButton").addEventListener("click", async () => {
  const result = $("#aiResult"); result.textContent = "Analysing deadlines, priorities and progress…";
  try {
    const body = await api("/ai/recommendations", { method: "POST", body: JSON.stringify({ student_id: $("#studentFilter").value.trim() }) });
    result.textContent = body.recommendation;
  } catch (error) { result.textContent = `${error.message}. Make sure Ollama and the configured Qwen/Llama model are running.`; }
});

$("#addButton").addEventListener("click", () => openAssignmentForm());
$("#aiButton").addEventListener("click", () => { $("#aiModal").hidden = false; });
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => { $(`#${button.dataset.close}`).hidden = true; }));
["#studentFilter", "#statusFilter", "#priorityFilter", "#sortFilter"].forEach((selector) => $(selector).addEventListener("change", loadAssignments));
loadAssignments();

const multiAgent = {
  workflowId: null,
  run: $("#multiAgentRun"),
  request: $("#multiAgentRequest"),
  reason: $("#multiAgentReason"),
  status: $("#multiAgentStatus"),
  decision: $("#multiAgentDecision"),
  buttons: [...document.querySelectorAll("[data-human-decision]")],
};

function enableHumanReview(enabled) {
  multiAgent.buttons.forEach((button) => { button.disabled = !enabled; });
}

multiAgent.run.addEventListener("click", async () => {
  multiAgent.workflowId = null;
  enableHumanReview(false);
  multiAgent.run.disabled = true;
  multiAgent.reason.value = "";
  multiAgent.decision.textContent = "No human decision recorded.";
  multiAgent.status.textContent = "Running Planner → Worker → Reviewer…";
  ["Planner", "Worker", "Reviewer"].forEach((role) => {
    $(`#multiAgent${role}`).textContent = "Awaiting workflow.";
  });

  try {
    const result = await api("/multi-agent/assignment-workflow", {
      method: "POST",
      body: JSON.stringify({
        user_request: multiAgent.request.value.trim(),
        student_id: $("#studentFilter").value.trim(),
      }),
    });
    ["planner", "worker", "reviewer"].forEach((role) => {
      const target = `#multiAgent${role[0].toUpperCase()}${role.slice(1)}`;
      $(target).textContent = JSON.stringify(result[`${role}_result`], null, 2);
    });
    if (
      result.workflow_id
      && result.reviewer_result
      && result.human_review?.status === "pending"
    ) {
      multiAgent.workflowId = result.workflow_id;
      enableHumanReview(true);
      multiAgent.status.textContent = `Workflow ${result.workflow_id}: awaiting your review.`;
    } else {
      throw new Error("The workflow did not return a pending human review.");
    }
  } catch (error) {
    multiAgent.status.textContent = error.message;
  } finally {
    multiAgent.run.disabled = false;
  }
});

multiAgent.buttons.forEach((button) => button.addEventListener("click", async () => {
  if (!multiAgent.workflowId) return;
  enableHumanReview(false);
  multiAgent.run.disabled = true;
  try {
    const result = await api(
      `/multi-agent/assignment-workflow/${encodeURIComponent(multiAgent.workflowId)}/decision`,
      {
        method: "POST",
        body: JSON.stringify({
          decision: button.dataset.humanDecision,
          reason: multiAgent.reason.value.trim(),
        }),
      },
    );
    const reason = result.human_review.reason || "None supplied";
    multiAgent.decision.textContent = `Final decision: ${result.human_review.decision}. Reason: ${reason}`;
    multiAgent.status.textContent = "Human review completed.";
    multiAgent.workflowId = null;
  } catch (error) {
    multiAgent.status.textContent = error.message;
    enableHumanReview(true);
  } finally {
    multiAgent.run.disabled = false;
  }
}));

// Load saved Agent Trace
const storedTrace =
  localStorage.getItem("student3AgentTrace");

const traceEmpty =
  document.getElementById("traceEmpty");

const traceContent =
  document.getElementById("traceContent");

if (!storedTrace) {
  traceEmpty.hidden = false;
} else {
  try {
    const trace = JSON.parse(storedTrace);

    document.getElementById("traceQuestion").textContent =
      trace.question || "Unknown request";

    document.getElementById("traceMode").textContent =
      `${(trace.mode || "ai").toUpperCase()} MODE`;

    const time =
      trace.timestamp
        ? new Date(trace.timestamp)
        : new Date();

    document.getElementById("traceTime").textContent =
      time.toLocaleString();

    document.getElementById("tracePlan").textContent =
      trace.plan || "No plan recorded.";

    document.getElementById("traceAct").textContent =
      trace.act || "No action recorded.";

    document.getElementById("traceObserve").textContent =
      trace.observe || "No observation recorded.";

    document.getElementById("traceAdapt").textContent =
      trace.adapt || "No adaptation recorded.";

    document.getElementById("traceResult").textContent =
      trace.result || "No final result recorded.";

    const details =
      document.getElementById("traceDetails");

    const traceDetails =
      Array.isArray(trace.details)
        ? trace.details
        : [];

    details.innerHTML = "";

    traceDetails.forEach(detail => {
      const card =
        document.createElement("div");

      card.className =
        "trace-detail";

      const label =
        document.createElement("span");

      label.className =
        "trace-detail-label";

      label.textContent =
        detail.label || "";

      const value =
        document.createElement("span");

      value.className =
        "trace-detail-value";

      value.textContent =
        detail.value ?? "N/A";

      card.appendChild(label);
      card.appendChild(value);
      details.appendChild(card);
    });

    if (traceDetails.length > 0) {
      details.removeAttribute("hidden");
      details.style.display = "grid";
    } else {
      details.hidden = true;
      details.style.display = "none";
    }


    // Multi-Agent mode uses the same four-step layout,
    // with labels reflecting the actual agent roles.
    const multiAgent = trace.mode === "multi-agent";

    const headings = {
      tracePlanHeading: multiAgent ? "PLANNER" : "PLAN",
      traceActHeading: multiAgent ? "WORKER" : "ACT",
      traceObserveHeading: multiAgent ? "REVIEWER" : "OBSERVE",
      traceAdaptHeading: multiAgent ? "HUMAN REVIEW" : "ADAPT"
    };

    Object.entries(headings).forEach(([id, value]) => {
      document.getElementById(id).textContent = value;
    });

    const statusText = document.getElementById("traceStatusText");
    const statusElement = document.getElementById("traceStatus");

    if (multiAgent) {
      const completed = trace.status === "completed";

      statusText.textContent = completed
        ? "COMPLETED"
        : trace.status === "pending_human_review"
          ? "PENDING HUMAN REVIEW"
          : (trace.status || "UNKNOWN").replaceAll("_", " ").toUpperCase();

      statusElement.classList.toggle("trace-pending", !completed);
    } else {
      statusText.textContent = "TRACE RECORDED";
    }

    traceContent.hidden = false;

  } catch (error) {
    console.error(
      "Failed to load Agent Trace:",
      error
    );

    traceEmpty.hidden = false;
  }
}
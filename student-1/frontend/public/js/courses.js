const API_BASE_URL = "/api/courses";

const state = {courses: [], selectedCourseId: null};
const elements = {
    addButton: document.getElementById("add-course-button"),
    alert: document.getElementById("alert"),
    cancelButton: document.getElementById("cancel-button"),
    closeButton: document.getElementById("close-dialog-button"),
    count: document.getElementById("course-count"),
    details: document.getElementById("course-details"),
    dialog: document.getElementById("course-dialog"),
    form: document.getElementById("course-form"),
    courseId: document.getElementById("course-id"),
    search: document.getElementById("course-search"),
    tableBody: document.getElementById("course-table-body"),
    formError: document.getElementById("form-error"),
    formTitle: document.getElementById("form-title"),
    generateAdviceButton: document.getElementById("generate-advice-button"),
    aiResult: document.getElementById("ai-result"),
    agenticTrace: document.getElementById("agentic-trace"),
    mcpCourseCode: document.getElementById("mcp-course-code"),
    mcpCourseCodeButton: document.getElementById("mcp-course-code-button"),
    mcpCourseCountButton: document.getElementById("mcp-course-count-button"),
    mcpProjectFilesButton: document.getElementById("mcp-project-files-button"),
    mcpResult: document.getElementById("mcp-result"),
    ragAnswerButton: document.getElementById("rag-answer-button"),
    ragQuery: document.getElementById("rag-query"),
    ragResult: document.getElementById("rag-result"),
    release1CourseCode: document.getElementById("release1-course-code"),
    release1CourseCodeField: document.getElementById("release1-course-code-field"),
    release1McpAction: document.getElementById("release1-mcp-action"),
    release1McpInputs: document.getElementById("release1-mcp-inputs"),
    release1PaoaMode: document.getElementById("release1-paoa-mode"),
    release1PaoaResult: document.getElementById("release1-paoa-result"),
    release1PaoaRunButton: document.getElementById("release1-paoa-run-button"),
    release1RagInputs: document.getElementById("release1-rag-inputs"),
    release1RagQuery: document.getElementById("release1-rag-query"),
    saveButton: document.getElementById("save-course-button"),
};

async function apiRequest(url, options = {}) {
    let response;
    try {
        response = await fetch(url, options);
    } catch (error) {
        throw new Error("The Course Management service is unavailable.");
    }

    let body;
    try {
        body = await response.json();
    } catch (error) {
        throw new Error("The server returned an invalid response.");
    }

    if (!response.ok) {
        throw new Error(body.error || `Request failed with status ${response.status}.`);
    }
    return body;
}

function showAlert(message, type) {
    elements.alert.textContent = message;
    elements.alert.className = `alert alert-${type}`;
    elements.alert.hidden = false;
    window.clearTimeout(showAlert.timeoutId);
    showAlert.timeoutId = window.setTimeout(() => {
        elements.alert.hidden = true;
    }, 5000);
}

function actionButton(label, className, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", handler);
    return button;
}

function renderCourses(courses) {
    elements.tableBody.replaceChildren();
    elements.count.textContent = `${courses.length} course${courses.length === 1 ? "" : "s"}`;

    if (courses.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 6;
        cell.className = "empty-state";
        cell.textContent = "No courses found.";
        row.appendChild(cell);
        elements.tableBody.appendChild(row);
        return;
    }

    courses.forEach((course) => {
        const row = document.createElement("tr");
        [
            course.course_code,
            course.course_name,
            course.lecturer,
            course.semester,
            course.credit_points,
        ].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "";
            row.appendChild(cell);
        });

        const actions = document.createElement("td");
        actions.className = "table-actions";
        actions.append(
            actionButton("View", "table-button", () => viewCourse(course.course_id)),
            actionButton("Edit", "table-button", () => openEditDialog(course.course_id)),
            actionButton("Delete", "table-button table-button-danger", () => deleteCourse(course))
        );
        row.appendChild(actions);
        elements.tableBody.appendChild(row);
    });
}

function filterCourses() {
    const query = elements.search.value.trim().toLowerCase();
    const courses = query
        ? state.courses.filter((course) =>
            [course.course_code, course.course_name, course.lecturer, course.semester]
                .some((value) => String(value ?? "").toLowerCase().includes(query)))
        : state.courses;
    renderCourses(courses);
}

async function loadCourses() {
    try {
        state.courses = await apiRequest(API_BASE_URL);
        filterCourses();
    } catch (error) {
        state.courses = [];
        renderCourses([]);
        showAlert(error.message, "error");
    }
}

function addDetail(container, label, value) {
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value ?? "";
    container.append(term, description);
}

function renderDetails(course) {
    const list = document.createElement("dl");
    list.className = "detail-list";
    addDetail(list, "Course ID", course.course_id);
    addDetail(list, "Course code", course.course_code);
    addDetail(list, "Course name", course.course_name);
    addDetail(list, "Lecturer", course.lecturer);
    addDetail(list, "Semester", course.semester);
    addDetail(list, "Credit points", course.credit_points);
    addDetail(list, "Description", course.course_description);
    elements.details.replaceChildren(list);
}

function renderAiResult(message, className = "") {
    const content = document.createElement("p");
    content.className = className;
    content.textContent = message;
    elements.aiResult.replaceChildren(content);
}

function renderMcpMessage(message, className = "") {
    const content = document.createElement("p");
    content.className = className;
    content.textContent = message;
    elements.mcpResult.replaceChildren(content);
}

function setMcpButtonsDisabled(disabled) {
    elements.mcpCourseCountButton.disabled = disabled;
    elements.mcpCourseCodeButton.disabled = disabled;
    elements.mcpProjectFilesButton.disabled = disabled;
}

async function requestMcpResult(url, expectedTool) {
    let response;
    try {
        response = await apiRequest(url);
    } catch (error) {
        throw new Error("MCP service is currently unavailable.");
    }

    if (
        !response
        || typeof response !== "object"
        || response.tool !== expectedTool
        || !Object.prototype.hasOwnProperty.call(response, "result")
    ) {
        throw new Error("MCP service returned an invalid response.");
    }

    if (
        response.result
        && typeof response.result === "object"
        && !Array.isArray(response.result)
        && response.result.error
    ) {
        throw new Error(String(response.result.error));
    }

    return response.result;
}

async function runMcpAction(loadingMessage, action) {
    setMcpButtonsDisabled(true);
    renderMcpMessage(loadingMessage, "muted");

    try {
        await action();
    } catch (error) {
        renderMcpMessage(error.message, "mcp-error");
    } finally {
        setMcpButtonsDisabled(false);
    }
}

async function loadMcpCourseCount() {
    await runMcpAction("Loading course count…", async () => {
        const result = await requestMcpResult(
            "/api/mcp/course-count",
            "course_count"
        );
        if (!result || !Number.isInteger(result.course_count)) {
            throw new Error("MCP service returned an invalid course count.");
        }
        renderMcpMessage(`Course Count: ${result.course_count}`, "mcp-success");
    });
}

async function loadMcpCourseByCode() {
    const courseCode = elements.mcpCourseCode.value.trim();
    if (!courseCode) {
        renderMcpMessage("Enter a course code.", "mcp-error");
        elements.mcpCourseCode.focus();
        return;
    }

    await runMcpAction("Finding course…", async () => {
        const result = await requestMcpResult(
            `/api/mcp/course-by-code/${encodeURIComponent(courseCode)}`,
            "course_by_code"
        );
        if (!result || typeof result !== "object" || Array.isArray(result)) {
            throw new Error("MCP service returned an invalid course record.");
        }

        const details = document.createElement("dl");
        details.className = "detail-list";
        addDetail(details, "Course Code", result.course_code);
        addDetail(details, "Course Name", result.course_name);
        addDetail(details, "Lecturer", result.lecturer);
        addDetail(details, "Semester", result.semester);
        addDetail(details, "Credit Points", result.credit_points);
        elements.mcpResult.replaceChildren(details);
    });
}

async function loadMcpProjectFiles() {
    await runMcpAction("Loading project files…", async () => {
        const result = await requestMcpResult(
            "/api/mcp/project-files",
            "project_files"
        );
        if (!Array.isArray(result)) {
            throw new Error("MCP service returned an invalid project file list.");
        }

        const list = document.createElement("ul");
        list.className = "mcp-file-list";
        result.forEach((name) => {
            const item = document.createElement("li");
            item.textContent = String(name);
            list.appendChild(item);
        });
        elements.mcpResult.replaceChildren(list);
    });
}

function renderRagMessage(message, className = "") {
    const content = document.createElement("p");
    content.className = className;
    content.textContent = message;
    elements.ragResult.replaceChildren(content);
}

function createRagSection(title) {
    const section = document.createElement("section");
    section.className = "rag-result-section";
    const heading = document.createElement("h3");
    heading.textContent = title;
    section.appendChild(heading);
    return section;
}

function renderRagAnswer(result) {
    const fragment = document.createDocumentFragment();

    const answerSection = createRagSection("Grounded Answer");
    const answer = document.createElement("p");
    answer.className = result.insufficient_context
        ? "rag-warning"
        : "rag-answer-text";
    answer.textContent = result.answer;
    answerSection.appendChild(answer);
    fragment.appendChild(answerSection);

    const confidenceSection = createRagSection("Confidence");
    const confidence = document.createElement("p");
    confidence.className = `rag-confidence rag-confidence-${result.confidence}`;
    confidence.textContent = result.confidence.charAt(0).toUpperCase()
        + result.confidence.slice(1);
    confidenceSection.appendChild(confidence);
    fragment.appendChild(confidenceSection);

    const sourcesSection = createRagSection("Sources");
    if (result.citations.length === 0) {
        const noSources = document.createElement("p");
        noSources.className = "muted";
        noSources.textContent = "No relevant sources found.";
        sourcesSection.appendChild(noSources);
    } else {
        const sources = document.createElement("ul");
        sources.className = "rag-source-list";
        result.citations.forEach((citation) => {
            const item = document.createElement("li");
            item.textContent = citation;
            sources.appendChild(item);
        });
        sourcesSection.appendChild(sources);
    }
    fragment.appendChild(sourcesSection);

    const contextSection = createRagSection("Retrieved Context");
    if (result.retrieved_context.length === 0) {
        const noContext = document.createElement("p");
        noContext.className = "muted";
        noContext.textContent = "No relevant Course Management context retrieved.";
        contextSection.appendChild(noContext);
    } else {
        const contextGrid = document.createElement("div");
        contextGrid.className = "rag-context-grid";
        result.retrieved_context.forEach((match) => {
            const course = match.context;
            const contextCard = document.createElement("article");
            contextCard.className = "rag-context-card";
            const details = document.createElement("dl");
            details.className = "detail-list";
            addDetail(details, "Course Code", course.course_code);
            addDetail(details, "Course Name", course.course_name);
            addDetail(details, "Lecturer", course.lecturer);
            addDetail(details, "Semester", course.semester);
            addDetail(details, "Credit Points", course.credit_points);
            contextCard.appendChild(details);
            contextGrid.appendChild(contextCard);
        });
        contextSection.appendChild(contextGrid);
    }
    fragment.appendChild(contextSection);

    elements.ragResult.replaceChildren(fragment);
}

function validateRagAnswer(result) {
    return Boolean(
        result
        && typeof result === "object"
        && typeof result.answer === "string"
        && ["high", "medium", "low"].includes(result.confidence)
        && typeof result.insufficient_context === "boolean"
        && Array.isArray(result.citations)
        && result.citations.every((citation) => typeof citation === "string")
        && Array.isArray(result.retrieved_context)
        && result.retrieved_context.every((match) => (
            match
            && typeof match === "object"
            && match.context
            && typeof match.context === "object"
        ))
    );
}

function ragErrorMessage(error) {
    if (error.message === "AI service unavailable") {
        return "AI service is currently unavailable.";
    }
    if (
        error.message === "RAG server unavailable"
        || error.message === "RAG retrieval failed"
    ) {
        return "RAG service is currently unavailable.";
    }
    return "Unable to retrieve a grounded course answer.";
}

async function loadRagAnswer() {
    const query = elements.ragQuery.value.trim();
    if (!query) {
        renderRagMessage(
            "Please enter a course-related question.",
            "rag-error"
        );
        elements.ragQuery.focus();
        return;
    }

    elements.ragAnswerButton.disabled = true;
    elements.ragAnswerButton.textContent = "Retrieving…";
    renderRagMessage(
        "Retrieving grounded Course Management context...",
        "muted"
    );

    try {
        const result = await apiRequest("/api/rag/answer", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({query, top_k: 3}),
        });
        if (!validateRagAnswer(result)) {
            throw new Error("Invalid RAG response");
        }
        renderRagAnswer(result);
    } catch (error) {
        renderRagMessage(ragErrorMessage(error), "rag-error");
    } finally {
        elements.ragAnswerButton.disabled = false;
        elements.ragAnswerButton.textContent = "Ask with RAG";
    }
}

function formatPaoaLabel(value) {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function appendPaoaField(container, label, value) {
    const row = document.createElement("div");
    row.className = "release1-paoa-field";
    const name = document.createElement("strong");
    name.textContent = label;
    const content = document.createElement("span");
    content.textContent = typeof value === "boolean"
        ? (value ? "Yes" : "No")
        : String(value ?? "None");
    row.append(name, content);
    container.appendChild(row);
}

function createRelease1PaoaStage(title, stageClass = "") {
    const stage = document.createElement("section");
    stage.className = `release1-paoa-stage ${stageClass}`.trim();
    const heading = document.createElement("h3");
    heading.textContent = title;
    stage.appendChild(heading);
    return stage;
}

function renderRelease1PaoaPlan(plan) {
    const stage = createRelease1PaoaStage("Plan", "release1-stage-plan");
    Object.entries(plan).forEach(([key, value]) => {
        appendPaoaField(stage, formatPaoaLabel(key), value);
    });
    return stage;
}

function renderRelease1PaoaAct(act) {
    const stage = createRelease1PaoaStage("Act", "release1-stage-act");
    Object.entries(act).forEach(([key, value]) => {
        if (key === "arguments" && value && typeof value === "object") {
            Object.entries(value).forEach(([argument, argumentValue]) => {
                appendPaoaField(
                    stage,
                    `Argument: ${formatPaoaLabel(argument)}`,
                    argumentValue
                );
            });
        } else {
            appendPaoaField(stage, formatPaoaLabel(key), value);
        }
    });
    return stage;
}

function renderRelease1PaoaObserve(observe) {
    const stage = createRelease1PaoaStage("Observe", "release1-stage-observe");
    appendPaoaField(stage, "Valid", observe.valid);
    if (Object.prototype.hasOwnProperty.call(observe, "grounding_available")) {
        appendPaoaField(
            stage,
            "Grounding Available",
            observe.grounding_available
        );
    }
    if (observe.reason) appendPaoaField(stage, "Reason", observe.reason);
    if (observe.attempt) appendPaoaField(stage, "Attempt", observe.attempt);
    if (Array.isArray(observe.checks)) {
        const label = document.createElement("strong");
        label.textContent = "Checks";
        const checks = document.createElement("ul");
        observe.checks.forEach((check) => {
            const item = document.createElement("li");
            item.textContent = String(check);
            checks.appendChild(item);
        });
        stage.append(label, checks);
    }
    return stage;
}

function renderRelease1PaoaAdapt(adapt) {
    const stage = createRelease1PaoaStage("Adapt", "release1-stage-adapt");
    appendPaoaField(stage, "Performed", adapt.performed);
    if (adapt.reason) appendPaoaField(stage, "Reason", adapt.reason);
    if (Object.prototype.hasOwnProperty.call(adapt, "retry_count")) {
        appendPaoaField(stage, "Retry Count", adapt.retry_count);
    }
    return stage;
}

function renderRelease1RagFinalResult(stage, result) {
    if (result.error) {
        appendPaoaField(stage, "Error", result.error);
        if (result.detail) appendPaoaField(stage, "Detail", result.detail);
        return;
    }

    appendPaoaField(stage, "Grounded Answer", result.answer);
    appendPaoaField(stage, "Confidence", formatPaoaLabel(result.confidence));
    appendPaoaField(stage, "Insufficient Context", result.insufficient_context);

    const sourcesLabel = document.createElement("strong");
    sourcesLabel.textContent = "Sources";
    stage.appendChild(sourcesLabel);
    if (Array.isArray(result.citations) && result.citations.length > 0) {
        const sources = document.createElement("ul");
        result.citations.forEach((citation) => {
            const item = document.createElement("li");
            item.textContent = String(citation);
            sources.appendChild(item);
        });
        stage.appendChild(sources);
    } else {
        const noSources = document.createElement("p");
        noSources.className = "muted";
        noSources.textContent = "No relevant sources found.";
        stage.appendChild(noSources);
    }

    const contextLabel = document.createElement("strong");
    contextLabel.textContent = "Retrieved Context";
    stage.appendChild(contextLabel);
    if (Array.isArray(result.retrieved_context) && result.retrieved_context.length > 0) {
        result.retrieved_context.forEach((match) => {
            const course = match.context;
            const details = document.createElement("dl");
            details.className = "detail-list release1-context-detail";
            addDetail(details, "Course Code", course.course_code);
            addDetail(details, "Course Name", course.course_name);
            addDetail(details, "Lecturer", course.lecturer);
            addDetail(details, "Semester", course.semester);
            addDetail(details, "Credit Points", course.credit_points);
            stage.appendChild(details);
        });
    } else {
        const noContext = document.createElement("p");
        noContext.className = "muted";
        noContext.textContent = "No relevant Course Management context retrieved.";
        stage.appendChild(noContext);
    }
}

function renderRelease1McpFinalResult(stage, result) {
    if (Array.isArray(result)) {
        const list = document.createElement("ul");
        result.forEach((value) => {
            const item = document.createElement("li");
            item.textContent = String(value);
            list.appendChild(item);
        });
        stage.appendChild(list);
        return;
    }

    if (result && typeof result === "object") {
        const labels = {
            course_count: "Course Count",
            course_code: "Course Code",
            course_name: "Course Name",
            lecturer: "Lecturer",
            semester: "Semester",
            credit_points: "Credit Points",
        };
        let renderedFields = 0;
        Object.entries(labels).forEach(([key, label]) => {
            if (Object.prototype.hasOwnProperty.call(result, key)) {
                appendPaoaField(stage, label, result[key]);
                renderedFields += 1;
            }
        });
        if (renderedFields === 0) {
            Object.entries(result).forEach(([key, value]) => {
                appendPaoaField(stage, formatPaoaLabel(key), value);
            });
        }
        return;
    }

    appendPaoaField(stage, "Result", result);
}

function renderRelease1PaoaFinalResult(mode, result) {
    const stage = createRelease1PaoaStage(
        "Final Result",
        "release1-stage-final"
    );
    if (mode === "rag") {
        renderRelease1RagFinalResult(stage, result);
    } else {
        renderRelease1McpFinalResult(stage, result);
    }
    return stage;
}

function renderRelease1PaoaTrace(trace) {
    const sequence = document.createElement("div");
    sequence.className = "release1-paoa-sequence";
    const stages = [
        renderRelease1PaoaPlan(trace.plan),
        renderRelease1PaoaAct(trace.act),
        renderRelease1PaoaObserve(trace.observe),
        renderRelease1PaoaAdapt(trace.adapt),
        renderRelease1PaoaFinalResult(trace.mode, trace.final_result),
    ];
    stages.forEach((stage, index) => {
        sequence.appendChild(stage);
        if (index < stages.length - 1) {
            const arrow = document.createElement("span");
            arrow.className = "release1-paoa-arrow";
            arrow.textContent = "↓";
            sequence.appendChild(arrow);
        }
    });
    elements.release1PaoaResult.replaceChildren(sequence);
}

function renderRelease1PaoaMessage(message, className = "") {
    const content = document.createElement("p");
    content.className = className;
    content.textContent = message;
    elements.release1PaoaResult.replaceChildren(content);
}

function updateRelease1McpAction() {
    elements.release1CourseCodeField.hidden = (
        elements.release1McpAction.value !== "course_by_code"
    );
}

function updateRelease1PaoaMode() {
    const isMcp = elements.release1PaoaMode.value === "mcp";
    elements.release1McpInputs.hidden = !isMcp;
    elements.release1RagInputs.hidden = isMcp;
    elements.release1PaoaRunButton.textContent = isMcp
        ? "Run MCP PAOA"
        : "Run RAG PAOA";
    if (isMcp) updateRelease1McpAction();
}

function release1PaoaErrorMessage(error) {
    const serviceMessages = {
        "MCP server unavailable": "MCP service is currently unavailable.",
        "RAG server unavailable": "RAG service is currently unavailable.",
        "AI service unavailable": "AI service is currently unavailable.",
    };
    return serviceMessages[error.message] || error.message;
}

async function requestRelease1Paoa(payload) {
    let response;
    try {
        response = await fetch("/api/agentic/release1/validate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });
    } catch (error) {
        throw new Error("The Course Management service is unavailable.");
    }

    let body;
    try {
        body = await response.json();
    } catch (error) {
        throw new Error("The server returned an invalid response.");
    }

    const isTrace = body
        && typeof body === "object"
        && body.plan
        && body.act
        && body.observe
        && body.adapt
        && Object.prototype.hasOwnProperty.call(body, "final_result");
    if (!response.ok && !isTrace) {
        throw new Error(body.error || `Request failed with status ${response.status}.`);
    }
    if (!isTrace) throw new Error("The server returned an invalid PAOA trace.");
    return body;
}

async function runRelease1Paoa() {
    const mode = elements.release1PaoaMode.value;
    const payload = {mode};

    if (mode === "mcp") {
        payload.action = elements.release1McpAction.value;
        if (payload.action === "course_by_code") {
            const courseCode = elements.release1CourseCode.value.trim();
            if (!courseCode) {
                renderRelease1PaoaMessage(
                    "Please enter a course code.",
                    "release1-paoa-error"
                );
                elements.release1CourseCode.focus();
                return;
            }
            payload.course_code = courseCode;
        }
    } else {
        const query = elements.release1RagQuery.value.trim();
        if (!query) {
            renderRelease1PaoaMessage(
                "Please enter a course-related question.",
                "release1-paoa-error"
            );
            elements.release1RagQuery.focus();
            return;
        }
        payload.query = query;
        payload.top_k = 3;
    }

    elements.release1PaoaRunButton.disabled = true;
    renderRelease1PaoaMessage(
        "Running Plan → Act → Observe → Adapt...",
        "muted"
    );

    try {
        const trace = await requestRelease1Paoa(payload);
        renderRelease1PaoaTrace(trace);
    } catch (error) {
        renderRelease1PaoaMessage(
            release1PaoaErrorMessage(error),
            "release1-paoa-error"
        );
    } finally {
        elements.release1PaoaRunButton.disabled = false;
    }
}

function renderAgenticTrace(trace = []) {
    const traceByPhase = new Map(trace.map((item) => [item.phase, item]));
    const fragment = document.createDocumentFragment();

    ["plan", "act", "observe", "adapt"].forEach((phase, index) => {
        const item = traceByPhase.get(phase);
        const stage = document.createElement("div");
        stage.className = `agentic-stage agentic-stage-${item?.status || "pending"}`;

        const name = document.createElement("strong");
        name.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
        const status = document.createElement("span");
        status.textContent = item?.status?.replace("_", " ") || "pending";
        const detail = document.createElement("small");
        detail.textContent = item?.detail || "Waiting to run";
        stage.append(name, status, detail);
        fragment.appendChild(stage);

        if (index < 3) {
            const arrow = document.createElement("span");
            arrow.className = "agentic-arrow";
            arrow.textContent = "→";
            fragment.appendChild(arrow);
        }
    });

    elements.agenticTrace.replaceChildren(fragment);
}

function resetAssistant(enabled = false) {
    elements.generateAdviceButton.disabled = !enabled;
    elements.generateAdviceButton.textContent = "Generate Study Advice";
    renderAiResult(
        enabled
            ? "Ready to generate advice for the selected course."
            : "View a course to activate the assistant.",
        "muted"
    );
    renderAgenticTrace();
}

async function viewCourse(courseId) {
    try {
        const course = await apiRequest(`${API_BASE_URL}/${courseId}`);
        state.selectedCourseId = courseId;
        renderDetails(course);
        resetAssistant(true);
    } catch (error) {
        showAlert(error.message, "error");
    }
}

function setFormError(message = "") {
    elements.formError.textContent = message;
    elements.formError.hidden = !message;
}

function openAddDialog() {
    elements.form.reset();
    elements.courseId.value = "";
    elements.formTitle.textContent = "Add Course";
    elements.saveButton.textContent = "Add Course";
    setFormError();
    elements.dialog.showModal();
}

async function openEditDialog(courseId) {
    try {
        const course = await apiRequest(`${API_BASE_URL}/${courseId}`);
        elements.courseId.value = course.course_id;
        elements.form.elements.course_code.value = course.course_code;
        elements.form.elements.course_name.value = course.course_name;
        elements.form.elements.lecturer.value = course.lecturer;
        elements.form.elements.semester.value = course.semester;
        elements.form.elements.credit_points.value = course.credit_points;
        elements.form.elements.course_description.value = course.course_description;
        elements.formTitle.textContent = "Edit Course";
        elements.saveButton.textContent = "Save Changes";
        setFormError();
        elements.dialog.showModal();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

function closeDialog() {
    elements.dialog.close();
    setFormError();
}

function formCourse() {
    const data = new FormData(elements.form);
    return {
        course_code: data.get("course_code").trim(),
        course_name: data.get("course_name").trim(),
        lecturer: data.get("lecturer").trim(),
        semester: data.get("semester").trim(),
        credit_points: Number(data.get("credit_points")),
        course_description: data.get("course_description").trim(),
    };
}

async function saveCourse(event) {
    event.preventDefault();
    setFormError();
    if (!elements.form.reportValidity()) return;

    const courseId = elements.courseId.value;
    const isEditing = Boolean(courseId);
    const url = isEditing ? `${API_BASE_URL}/${courseId}` : API_BASE_URL;
    elements.saveButton.disabled = true;

    try {
        await apiRequest(url, {
            method: isEditing ? "PUT" : "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(formCourse()),
        });
        closeDialog();
        showAlert(isEditing ? "Course updated successfully." : "Course added successfully.", "success");
        await loadCourses();
        if (isEditing && state.selectedCourseId === Number(courseId)) {
            await viewCourse(Number(courseId));
        }
    } catch (error) {
        setFormError(error.message);
    } finally {
        elements.saveButton.disabled = false;
    }
}

async function deleteCourse(course) {
    if (!window.confirm(`Delete ${course.course_code} – ${course.course_name}?`)) return;

    try {
        await apiRequest(`${API_BASE_URL}/${course.course_id}`, {method: "DELETE"});
        if (state.selectedCourseId === course.course_id) {
            state.selectedCourseId = null;
            const message = document.createElement("p");
            message.className = "muted";
            message.textContent = "Select View beside a course to see its details.";
            elements.details.replaceChildren(message);
            resetAssistant();
        }
        showAlert("Course deleted successfully.", "success");
        await loadCourses();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function generateStudyAdvice() {
    const courseId = state.selectedCourseId;
    if (!courseId) {
        renderAiResult("View a course before generating study advice.", "ai-error");
        return;
    }

    elements.generateAdviceButton.disabled = true;
    elements.generateAdviceButton.textContent = "Generating…";
    renderAiResult("Generating course summary and study recommendations…", "muted");
    renderAgenticTrace();

    try {
        const result = await apiRequest(
            `${API_BASE_URL}/${courseId}/recommendation`,
            {method: "POST"}
        );
        if (state.selectedCourseId === courseId) {
            renderAiResult(result.recommendation, "ai-response");
            renderAgenticTrace(result.agentic_trace);
        }
    } catch (error) {
        if (state.selectedCourseId === courseId) {
            renderAiResult(error.message, "ai-error");
        }
    } finally {
        if (state.selectedCourseId === courseId) {
            elements.generateAdviceButton.disabled = false;
            elements.generateAdviceButton.textContent = "Generate Study Advice";
        }
    }
}

elements.addButton.addEventListener("click", openAddDialog);
elements.cancelButton.addEventListener("click", closeDialog);
elements.closeButton.addEventListener("click", closeDialog);
elements.generateAdviceButton.addEventListener("click", generateStudyAdvice);
elements.mcpCourseCountButton.addEventListener("click", loadMcpCourseCount);
elements.mcpCourseCodeButton.addEventListener("click", loadMcpCourseByCode);
elements.mcpProjectFilesButton.addEventListener("click", loadMcpProjectFiles);
elements.ragAnswerButton.addEventListener("click", loadRagAnswer);
elements.release1McpAction.addEventListener("change", updateRelease1McpAction);
elements.release1PaoaMode.addEventListener("change", updateRelease1PaoaMode);
elements.release1PaoaRunButton.addEventListener("click", runRelease1Paoa);
elements.mcpCourseCode.addEventListener("keydown", (event) => {
    if (event.key === "Enter") loadMcpCourseByCode();
});
elements.form.addEventListener("submit", saveCourse);
elements.search.addEventListener("input", filterCourses);
elements.dialog.addEventListener("click", (event) => {
    if (event.target === elements.dialog) closeDialog();
});

loadCourses();
renderAgenticTrace();
updateRelease1PaoaMode();

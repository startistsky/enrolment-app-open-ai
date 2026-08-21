const API_BASE_URL = "http://localhost:8001/api/courses";

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

function resetAssistant(enabled = false) {
    elements.generateAdviceButton.disabled = !enabled;
    elements.generateAdviceButton.textContent = "Generate Study Advice";
    renderAiResult(
        enabled
            ? "Ready to generate advice for the selected course."
            : "View a course to activate the assistant.",
        "muted"
    );
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

    try {
        const result = await apiRequest(
            `${API_BASE_URL}/${courseId}/recommendation`,
            {method: "POST"}
        );
        if (state.selectedCourseId === courseId) {
            renderAiResult(result.recommendation, "ai-response");
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
elements.form.addEventListener("submit", saveCourse);
elements.search.addEventListener("input", filterCourses);
elements.dialog.addEventListener("click", (event) => {
    if (event.target === elements.dialog) closeDialog();
});

loadCourses();

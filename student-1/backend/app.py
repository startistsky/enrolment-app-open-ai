import asyncio
import json
import os
import re

import httpx2
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


app = Flask(__name__)
CORS(app, origins=["http://localhost:8081"])

DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL", "http://localhost:5001"
).rstrip("/")
AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL", "http://localhost:11434/api/generate"
)
AI_MODEL = "qwen2.5:0.5b"
REQUEST_TIMEOUT_SECONDS = 5
AI_REQUEST_TIMEOUT_SECONDS = 60
MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL", "http://host.docker.internal:9001/mcp"
).rstrip("/")
MCP_REQUEST_TIMEOUT_SECONDS = 10
RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL", "http://host.docker.internal:9101"
).rstrip("/")
RAG_REQUEST_TIMEOUT_SECONDS = 10

REQUIRED_COURSE_FIELDS = [
    "course_code",
    "course_name",
    "lecturer",
    "semester",
    "credit_points",
    "course_description",
]
TEXT_COURSE_FIELDS = [
    "course_code",
    "course_name",
    "lecturer",
    "semester",
    "course_description",
]


def _normalise_mcp_result(tool_result):
    """Convert an MCP tool result into a JSON-serialisable value."""
    structured_content = getattr(tool_result, "structured_content", None)
    if structured_content is not None:
        return structured_content

    content = getattr(tool_result, "content", [])
    if content and all(getattr(item, "type", None) == "text" for item in content):
        text_values = [item.text for item in content]
        if len(text_values) == 1:
            try:
                return json.loads(text_values[0])
            except (TypeError, ValueError):
                return text_values[0]

        return text_values

    return [
        item.model_dump(by_alias=True, mode="json")
        if hasattr(item, "model_dump")
        else str(item)
        for item in content
    ]


def _exception_contains(exception, exception_types):
    """Check an exception and any nested exception group for matching types."""
    if isinstance(exception, exception_types):
        return True

    nested_exceptions = getattr(exception, "exceptions", ())
    return any(
        _exception_contains(nested, exception_types)
        for nested in nested_exceptions
    )


def call_mcp_tool(tool_name, arguments=None):
    """Call a tool on the shared MCP server and return a safe result envelope."""
    async def invoke_tool():
        async with httpx2.AsyncClient(
            timeout=MCP_REQUEST_TIMEOUT_SECONDS
        ) as http_client:
            async with streamable_http_client(
                MCP_SERVER_URL,
                http_client=http_client,
            ) as streams:
                async with ClientSession(
                    streams[0],
                    streams[1],
                    read_timeout_seconds=MCP_REQUEST_TIMEOUT_SECONDS,
                ) as session:
                    await session.initialize()
                    return await session.call_tool(tool_name, arguments or {})

    try:
        tool_result = asyncio.run(invoke_tool())
    except Exception as exc:
        if _exception_contains(
            exc,
            (httpx2.ConnectError, httpx2.TimeoutException),
        ):
            return {
                "ok": False,
                "status": 503,
                "error": "MCP server unavailable",
                "detail": str(exc),
            }

        return {
            "ok": False,
            "status": 502,
            "error": "MCP protocol or tool invocation failed",
            "detail": str(exc),
        }

    if getattr(tool_result, "is_error", False):
        return {
            "ok": False,
            "status": 502,
            "error": "MCP tool invocation failed",
            "detail": _normalise_mcp_result(tool_result),
        }

    return {
        "ok": True,
        "result": _normalise_mcp_result(tool_result),
    }


def mcp_tool_response(tool_name, arguments=None):
    """Build a Flask response from the shared MCP tool call envelope."""
    outcome = call_mcp_tool(tool_name, arguments)
    if not outcome["ok"]:
        error_body = {
            key: value
            for key, value in outcome.items()
            if key not in {"ok", "status"}
        }
        return jsonify(error_body), outcome["status"]

    return jsonify({
        "tool": tool_name,
        "result": outcome["result"],
    })


def call_rag_course_retrieval(query, top_k=3):
    """Retrieve course context from the shared local RAG server."""
    try:
        response = requests.post(
            f"{RAG_SERVER_URL}/retrieve/course",
            json={
                "query": query,
                "top_k": top_k,
            },
            timeout=RAG_REQUEST_TIMEOUT_SECONDS,
        )
    except (requests.ConnectionError, requests.Timeout) as exc:
        return {
            "ok": False,
            "status": 503,
            "error": "RAG server unavailable",
            "detail": str(exc),
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": 502,
            "error": "RAG retrieval failed",
            "detail": str(exc),
        }

    if not response.ok:
        return {
            "ok": False,
            "status": 502,
            "error": "RAG retrieval failed",
            "detail": f"RAG server returned HTTP {response.status_code}",
        }

    try:
        result = response.json()
    except ValueError:
        return {
            "ok": False,
            "status": 502,
            "error": "RAG retrieval failed",
            "detail": "RAG server returned invalid JSON",
        }

    if not isinstance(result, dict):
        return {
            "ok": False,
            "status": 502,
            "error": "RAG retrieval failed",
            "detail": "RAG server response must be a JSON object",
        }

    return {
        "ok": True,
        "result": result,
    }


def generate_grounded_course_answer(query, retrieval_result):
    """Generate an answer using only the course records returned by RAG."""
    matches = retrieval_result.get("matches", [])
    retrieved_records = [
        match["context"]
        for match in matches
        if isinstance(match, dict) and isinstance(match.get("context"), dict)
    ]

    prompt = (
        "Answer the user's question using ONLY the supplied Course Management "
        "context. Do not use outside knowledge or invent course information. "
        "If the supplied context is insufficient, say that there is insufficient "
        "Course Management context. Keep the answer concise. Do not invent "
        "citations; citations are attached separately by the backend.\n\n"
        f"User question:\n{query}\n\n"
        "Retrieved Course Management context:\n"
        f"{json.dumps(retrieved_records, ensure_ascii=False, indent=2)}\n\n"
        "Use only the retrieved context."
    )

    return request_ai_recommendation(prompt)


def _error_from_outcome(outcome):
    """Remove internal control fields from an MCP or RAG error outcome."""
    return {
        key: value
        for key, value in outcome.items()
        if key not in {"ok", "status"}
    }


def _validate_mcp_result(action, result):
    """Validate an MCP result deterministically for a supported action."""
    checks = ["MCP invocation succeeded"]

    if action == "course_count":
        valid = (
            isinstance(result, dict)
            and isinstance(result.get("course_count"), int)
            and not isinstance(result.get("course_count"), bool)
            and result["course_count"] >= 0
        )
        if valid:
            checks.append("Course count is a non-negative integer")
        else:
            checks.append("Course count result failed structural validation")
        return valid, checks

    if action == "course_by_code":
        valid = isinstance(result, dict) and "error" not in result
        if valid and result.get("course_code"):
            checks.append("Course record contains course_code")
        else:
            valid = False
            checks.append("Course record is missing course_code")
        if valid and result.get("course_name"):
            checks.append("Course record contains course_name")
        else:
            valid = False
            checks.append("Course record is missing course_name")
        return valid, checks

    valid = isinstance(result, list)
    checks.append(
        "Project files result is a list"
        if valid
        else "Project files result failed structural validation"
    )
    return valid, checks


def _validate_rag_result(result):
    """Validate retrieved RAG evidence without asking an AI model."""
    if not isinstance(result, dict):
        return {
            "valid": False,
            "grounding_available": False,
            "reason": "RAG retrieval result must be an object.",
        }

    matches = result.get("matches")
    if not isinstance(matches, list):
        return {
            "valid": False,
            "grounding_available": False,
            "reason": "RAG matches must be a list.",
        }

    insufficient_context = result.get("insufficient_context")
    if not isinstance(insufficient_context, bool):
        return {
            "valid": False,
            "grounding_available": False,
            "reason": "RAG result must explicitly declare insufficient_context.",
        }

    if insufficient_context:
        return {
            "valid": True,
            "grounding_available": False,
            "reason": "No relevant Course Management context was retrieved.",
        }

    if not matches:
        return {
            "valid": False,
            "grounding_available": False,
            "reason": "A sufficient RAG result must contain at least one match.",
        }

    allowed_confidence = {"high", "medium", "low"}
    for match in matches:
        if not isinstance(match, dict):
            return {
                "valid": False,
                "grounding_available": False,
                "reason": "Every RAG match must be an object.",
            }
        if not isinstance(match.get("context"), dict):
            return {
                "valid": False,
                "grounding_available": False,
                "reason": "Every RAG match must contain course context.",
            }
        if not isinstance(match.get("citation"), str) or not match["citation"].strip():
            return {
                "valid": False,
                "grounding_available": False,
                "reason": "Every RAG match must contain a citation.",
            }
        if match.get("confidence") not in allowed_confidence:
            return {
                "valid": False,
                "grounding_available": False,
                "reason": "Every RAG match must contain a valid confidence category.",
            }

    return {
        "valid": True,
        "grounding_available": True,
        "reason": "Retrieved citations, confidence and course context passed validation.",
    }


def _build_rag_final_result(query, retrieval_result, answer=None):
    """Build deterministic grounded-answer metadata from RAG retrieval data."""
    matches = retrieval_result.get("matches", [])
    if retrieval_result.get("insufficient_context") is True or not matches:
        message = retrieval_result.get("message")
        if not isinstance(message, str) or not message.strip():
            message = "Insufficient context: no relevant Course Management information was found."
        return {
            "query": retrieval_result.get("query", query),
            "answer": message,
            "citations": [],
            "confidence": "low",
            "insufficient_context": True,
            "retrieved_context": [],
        }

    citations = []
    for match in matches:
        citation = match["citation"]
        if citation not in citations:
            citations.append(citation)

    return {
        "query": retrieval_result.get("query", query),
        "answer": answer,
        "citations": citations,
        "confidence": matches[0]["confidence"],
        "insufficient_context": False,
        "retrieved_context": matches,
    }


def run_release1_mcp_paoa(action, course_code=None):
    """Run one evidence-based PAOA cycle using an existing MCP helper."""
    supported_actions = {"course_count", "course_by_code", "project_files"}
    if action not in supported_actions:
        return {"error": "Unsupported MCP action"}, 400

    if action == "course_by_code":
        if not isinstance(course_code, str) or not course_code.strip():
            return {"error": "course_code is required"}, 400
        normalised_code = course_code.strip().upper()
        arguments = {"course_code": normalised_code}
    elif action == "project_files":
        arguments = {"directory_path": ".."}
    else:
        arguments = None

    trace = {
        "mode": "mcp",
        "plan": {
            "goal": "Retrieve verified Course Management information through the shared MCP server.",
            "action": action,
            "tool": action,
        },
        "act": {
            "tool": action,
            "arguments": arguments,
            "invocation_completed": False,
        },
    }

    outcome = call_mcp_tool(action, arguments)
    if not outcome["ok"]:
        return _error_from_outcome(outcome), outcome["status"]

    trace["act"]["invocation_completed"] = True
    result = outcome["result"]
    valid, checks = _validate_mcp_result(action, result)
    trace["observe"] = {"valid": valid, "checks": checks}

    if valid:
        trace["adapt"] = {
            "performed": False,
            "reason": "The MCP result passed validation; no corrective action was required.",
        }
    else:
        trace["adapt"] = {
            "performed": True,
            "reason": "The first MCP result failed validation, so one corrective tool retry was performed.",
            "retry_count": 1,
        }
        retry_outcome = call_mcp_tool(action, arguments)
        if not retry_outcome["ok"]:
            return _error_from_outcome(retry_outcome), retry_outcome["status"]
        result = retry_outcome["result"]
        valid, checks = _validate_mcp_result(action, result)
        trace["observe"] = {
            "valid": valid,
            "checks": checks,
            "attempt": "corrective_retry",
        }

    trace["final_result"] = result
    return trace, 200 if trace["observe"]["valid"] else 502


def run_release1_rag_paoa(query, top_k=3):
    """Run one evidence-based PAOA cycle using existing RAG and AI helpers."""
    safe_top_k = (
        min(top_k, 10)
        if isinstance(top_k, int) and not isinstance(top_k, bool) and top_k > 0
        else 3
    )
    trace = {
        "mode": "rag",
        "plan": {
            "goal": "Retrieve grounded Course Management context and validate the evidence before producing an AI-supported response.",
            "strategy": "Retrieve relevant course records from the shared RAG server and validate citations, confidence and context.",
        },
        "act": {
            "operation": "RAG course retrieval",
            "query": query,
            "top_k": top_k,
            "invocation_completed": False,
        },
    }

    outcome = call_rag_course_retrieval(query, top_k)
    if not outcome["ok"]:
        return _error_from_outcome(outcome), outcome["status"]

    trace["act"]["invocation_completed"] = True
    retrieval_result = outcome["result"]
    observation = _validate_rag_result(retrieval_result)
    trace["observe"] = observation

    if observation["valid"]:
        trace["adapt"] = {
            "performed": False,
            "reason": (
                "Retrieved RAG evidence passed grounding validation; no retrieval correction was required."
                if observation["grounding_available"]
                else "Insufficient context is a valid outcome; no corrective retrieval was required."
            ),
        }
    else:
        trace["adapt"] = {
            "performed": True,
            "reason": "The first RAG retrieval result failed grounding validation, so one corrective retrieval was performed.",
            "retry_count": 1,
        }
        retry_outcome = call_rag_course_retrieval(query, safe_top_k)
        if not retry_outcome["ok"]:
            return _error_from_outcome(retry_outcome), retry_outcome["status"]
        retrieval_result = retry_outcome["result"]
        observation = _validate_rag_result(retrieval_result)
        trace["observe"] = {
            **observation,
            "attempt": "corrective_retry",
        }

    if not trace["observe"]["valid"]:
        trace["final_result"] = {
            "error": "RAG retrieval failed",
            "detail": trace["observe"]["reason"],
        }
        return trace, 502

    if not trace["observe"]["grounding_available"]:
        trace["final_result"] = _build_rag_final_result(query, retrieval_result)
        return trace, 200

    answer, ai_error = generate_grounded_course_answer(query, retrieval_result)
    if ai_error:
        ai_response, status = ai_error
        return ai_response.get_json(), status

    trace["final_result"] = _build_rag_final_result(
        query,
        retrieval_result,
        answer,
    )
    return trace, 200


def database_request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{DATABASE_SERVICE_URL}{path}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        ), None
    except requests.RequestException:
        return None, (
            jsonify({"error": "Database service unavailable"}),
            503,
        )


def forward_database_response(response):
    try:
        body = response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from database service"}), 502

    return jsonify(body), response.status_code


def validate_course(data):
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    missing_fields = [
        field
        for field in REQUIRED_COURSE_FIELDS
        if field not in data or data[field] is None or data[field] == ""
    ]
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    for field in TEXT_COURSE_FIELDS:
        if not isinstance(data[field], str) or not data[field].strip():
            return None, f"{field} must be a non-empty string"

    raw_credit_points = data["credit_points"]
    if isinstance(raw_credit_points, bool):
        return None, "credit_points must be a positive integer"

    if isinstance(raw_credit_points, int):
        credit_points = raw_credit_points
    elif isinstance(raw_credit_points, str) and raw_credit_points.strip().isdigit():
        credit_points = int(raw_credit_points.strip())
    else:
        return None, "credit_points must be a positive integer"

    if credit_points <= 0:
        return None, "credit_points must be a positive integer"

    validated = {field: data[field] for field in REQUIRED_COURSE_FIELDS}
    for field in TEXT_COURSE_FIELDS:
        validated[field] = validated[field].strip()
    validated["credit_points"] = credit_points

    return validated, None


def course_code_exists(course_code, excluded_course_id=None):
    response, error = database_request("GET", "/courses")
    if error:
        return None, error

    try:
        courses = response.json()
    except ValueError:
        return None, (
            jsonify({"error": "Invalid response from database service"}),
            502,
        )

    if response.status_code != 200 or not isinstance(courses, list):
        return None, forward_database_response(response)

    duplicate = any(
        course.get("course_code") == course_code
        and course.get("course_id") != excluded_course_id
        for course in courses
    )
    return duplicate, None


def request_ai_recommendation(prompt):
    try:
        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return None, (jsonify({"error": "AI service request timed out"}), 504)
    except requests.RequestException:
        return None, (jsonify({"error": "AI service unavailable"}), 503)

    if not ai_response.ok:
        return None, (jsonify({"error": "AI service unavailable"}), 503)

    try:
        ai_body = ai_response.json()
    except ValueError:
        return None, (jsonify({"error": "Invalid response from AI service"}), 502)

    recommendation = ai_body.get("response") if isinstance(ai_body, dict) else None
    if not isinstance(recommendation, str) or not recommendation.strip():
        return None, (jsonify({"error": "Invalid response from AI service"}), 502)

    return recommendation.strip(), None


def validate_ai_recommendation(recommendation):
    if not recommendation.strip():
        return False, "The response was empty"

    has_summary = re.search(r"(?im)^\s*summary\s*:", recommendation)
    numbered_items = re.findall(r"(?m)^\s*(\d+)[.)]\s+\S.+$", recommendation)

    if not has_summary:
        return False, "The response did not include a labelled summary"
    if numbered_items != ["1", "2", "3"]:
        return False, "The response did not include exactly three numbered recommendations"

    return True, "The response contains a summary and exactly three recommendations"


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "course-backend"})


@app.get("/api/courses")
def list_courses():
    response, error = database_request("GET", "/courses")
    if error:
        return error
    return forward_database_response(response)


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    return forward_database_response(response)


@app.post("/api/courses")
def create_course():
    course, validation_error = validate_course(request.get_json(silent=True))
    if validation_error:
        return jsonify({"error": validation_error}), 400

    duplicate, error = course_code_exists(course["course_code"])
    if error:
        return error
    if duplicate:
        return jsonify({"error": "Course code already exists"}), 409

    response, error = database_request("POST", "/courses", json=course)
    if error:
        return error
    return forward_database_response(response)


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    course, validation_error = validate_course(request.get_json(silent=True))
    if validation_error:
        return jsonify({"error": validation_error}), 400

    existing_response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    if existing_response.status_code != 200:
        return forward_database_response(existing_response)

    duplicate, error = course_code_exists(
        course["course_code"], excluded_course_id=course_id
    )
    if error:
        return error
    if duplicate:
        return jsonify({"error": "Course code already exists"}), 409

    response, error = database_request(
        "PUT", f"/courses/{course_id}", json=course
    )
    if error:
        return error
    return forward_database_response(response)


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    response, error = database_request("DELETE", f"/courses/{course_id}")
    if error:
        return error
    return forward_database_response(response)


@app.post("/api/courses/<int:course_id>/recommendation")
def generate_course_recommendation(course_id):
    print(f"PLAN: Prepare study advice for course {course_id}.", flush=True)
    agentic_trace = [{
        "phase": "plan",
        "status": "completed",
        "detail": "Defined the goal: a concise summary and exactly three study recommendations",
    }]

    course_response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    if course_response.status_code != 200:
        return forward_database_response(course_response)

    try:
        course = course_response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from database service"}), 502

    if not isinstance(course, dict):
        return jsonify({"error": "Invalid response from database service"}), 502

    prompt = (
        "Create study advice using exactly this format:\n"
        "Summary: <one concise course summary>\n"
        "Study Recommendations:\n"
        "1. <practical recommendation>\n"
        "2. <practical recommendation>\n"
        "3. <practical recommendation>\n"
        "Keep the response concise.\n"
        f"Course: {course.get('course_code')} - {course.get('course_name')}\n"
        f"Lecturer: {course.get('lecturer')}\n"
        f"Semester: {course.get('semester')}\n"
        f"Credit points: {course.get('credit_points')}\n"
        f"Description: {course.get('course_description')}"
    )

    print("ACT: Retrieve course context and request advice from Ollama.", flush=True)
    recommendation, ai_error = request_ai_recommendation(prompt)
    if ai_error:
        return ai_error

    agentic_trace.append({
        "phase": "act",
        "status": "completed",
        "detail": "Retrieved the course and requested advice from Ollama",
    })

    is_valid, observation = validate_ai_recommendation(recommendation)
    print(f"OBSERVE: {observation}.", flush=True)
    agentic_trace.append({
        "phase": "observe",
        "status": "passed" if is_valid else "correction_required",
        "detail": observation,
    })

    if is_valid:
        print("ADAPT: Not required; the first response is valid.", flush=True)
        agentic_trace.append({
            "phase": "adapt",
            "status": "not_required",
            "detail": "The first response met the required structure; no retry was needed",
        })
    else:
        print("ADAPT: Correction required; sending one corrective prompt.", flush=True)
        adapted_prompt = (
            f"{prompt}\n\n"
            "Your previous response did not match the required structure. "
            f"Problem observed: {observation}. Correct it now and return only "
            "the requested Summary and three numbered Study Recommendations."
        )
        recommendation, ai_error = request_ai_recommendation(adapted_prompt)
        if ai_error:
            return ai_error

        corrected_is_valid, corrected_observation = validate_ai_recommendation(
            recommendation
        )
        if not corrected_is_valid:
            return jsonify({
                "error": "AI response did not match the required structure after one retry",
                "agentic_trace": agentic_trace + [{
                    "phase": "adapt",
                    "status": "failed",
                    "detail": corrected_observation,
                }],
            }), 502

        agentic_trace.append({
            "phase": "adapt",
            "status": "completed",
            "detail": "Sent one corrective prompt and accepted the corrected response",
        })

    print("PAOA workflow completed successfully.", flush=True)
    return jsonify({
        "course_id": course_id,
        "recommendation": recommendation,
        "agentic_trace": agentic_trace,
    })


@app.get("/api/mcp/course-count")
def mcp_course_count():
    return mcp_tool_response("course_count")


@app.get("/api/mcp/course-by-code/<course_code>")
def mcp_course_by_code(course_code):
    return mcp_tool_response(
        "course_by_code",
        {"course_code": course_code},
    )


@app.get("/api/mcp/project-files")
def mcp_project_files():
    directory_path = request.args.get("directory_path", "..")
    return mcp_tool_response(
        "project_files",
        {"directory_path": directory_path},
    )


@app.get("/api/mcp/ci-report")
def mcp_ci_report():
    report_path = request.args.get("report_path", "../reports/report.json")
    return mcp_tool_response(
        "ci_report",
        {"report_path": report_path},
    )


@app.post("/api/rag/course")
def rag_course_retrieval():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "error": "Request body must be a JSON object",
        }), 400

    outcome = call_rag_course_retrieval(
        body.get("query"),
        body.get("top_k", 3),
    )
    if not outcome["ok"]:
        error_body = {
            key: value
            for key, value in outcome.items()
            if key not in {"ok", "status"}
        }
        return jsonify(error_body), outcome["status"]

    return jsonify({"result": outcome["result"]})


@app.post("/api/rag/answer")
def rag_grounded_answer():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "error": "Request body must be a JSON object",
        }), 400

    query = body.get("query")
    retrieval_outcome = call_rag_course_retrieval(
        query,
        body.get("top_k", 3),
    )
    if not retrieval_outcome["ok"]:
        error_body = {
            key: value
            for key, value in retrieval_outcome.items()
            if key not in {"ok", "status"}
        }
        return jsonify(error_body), retrieval_outcome["status"]

    retrieval_result = retrieval_outcome["result"]
    matches = retrieval_result.get("matches", [])
    if not isinstance(matches, list):
        return jsonify({
            "error": "RAG retrieval failed",
            "detail": "RAG matches must be a list",
        }), 502

    usable_matches = [
        match
        for match in matches
        if isinstance(match, dict) and isinstance(match.get("context"), dict)
    ]
    if retrieval_result.get("insufficient_context") is True or not usable_matches:
        answer = retrieval_result.get("message")
        if not isinstance(answer, str) or not answer.strip():
            answer = "Insufficient context: no relevant Course Management information was found."

        return jsonify({
            "query": retrieval_result.get("query", query),
            "answer": answer,
            "citations": [],
            "confidence": "low",
            "insufficient_context": True,
            "retrieved_context": [],
        })

    answer, ai_error = generate_grounded_course_answer(
        query,
        {**retrieval_result, "matches": usable_matches},
    )
    if ai_error:
        return ai_error

    citations = []
    for match in usable_matches:
        citation = match.get("citation")
        if isinstance(citation, str) and citation not in citations:
            citations.append(citation)

    confidence = usable_matches[0].get("confidence", "low")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    return jsonify({
        "query": retrieval_result.get("query", query),
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "insufficient_context": False,
        "retrieved_context": usable_matches,
    })


@app.post("/api/agentic/release1/validate")
def validate_release1_agentic_workflow():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "error": "Request body must be a JSON object",
        }), 400

    mode = body.get("mode")
    if mode not in {"mcp", "rag"}:
        return jsonify({"error": "mode must be 'mcp' or 'rag'"}), 400

    if mode == "mcp":
        result, status = run_release1_mcp_paoa(
            body.get("action"),
            body.get("course_code"),
        )
    else:
        query = body.get("query")
        if not isinstance(query, str) or not query.strip():
            return jsonify({"error": "A RAG query is required"}), 400
        result, status = run_release1_rag_paoa(
            query.strip(),
            body.get("top_k", 3),
        )

    return jsonify(result), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)

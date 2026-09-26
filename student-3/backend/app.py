from rag_client import retrieve_resource_context
from mcp_client import call_mcp_tool
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
import requests


app = Flask(__name__)
CORS(app)


DATABASE_API_URL = os.getenv(
    "DATABASE_API_URL",
    "http://localhost:5004"
)

AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://ollama:11434/api/generate"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "qwen2.5:0.5b"
)


# =========================================================
# HEALTH
# =========================================================

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "Campus Resource Management Backend API"
    }), 200


# =========================================================
# CRUD PROXY
# =========================================================

@app.route("/resources", methods=["GET"])
def get_resources():
    try:
        response = requests.get(
            f"{DATABASE_API_URL}/resources",
            params=dict(request.args),
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    try:
        response = requests.get(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources", methods=["POST"])
def create_resource():
    try:
        response = requests.post(
            f"{DATABASE_API_URL}/resources",
            json=request.get_json(),
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    try:
        response = requests.put(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            json=request.get_json(),
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    try:
        response = requests.delete(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


# =========================================================
# AI HELPERS
# =========================================================

def normalise_text(text):
    return re.sub(
        r"[^a-z0-9\s]",
        " ",
        str(text).lower()
    )


RESOURCE_TYPE_KEYWORDS = {
    "Printer": [
        "printer",
        "printing",
        "print"
    ],

    "Computer Lab": [
        "computer lab",
        "computer",
        "lab"
    ],

    "Library": [
        "library"
    ],

    "Study Room": [
        "study room",
        "study space",
        "quiet",
        "study"
    ],

    "Parking": [
        "parking",
        "car park"
    ]
}


def detect_excluded_resource_types(question):
    text = normalise_text(question)

    excluded_types = set()

    negative_markers = [
        "not ",
        "no ",
        "without ",
        "do not recommend ",
        "dont recommend ",
        "do not want ",
        "dont want ",
        "avoid "
    ]

    for marker in negative_markers:

        if marker not in text:
            continue

        negative_part = text.split(
            marker,
            1
        )[1]

        for stop_word in [
            " but ",
            " instead ",
            " however "
        ]:
            if stop_word in negative_part:
                negative_part = negative_part.split(
                    stop_word,
                    1
                )[0]

        for resource_type, keywords in (
            RESOURCE_TYPE_KEYWORDS.items()
        ):

            if any(
                keyword in negative_part
                for keyword in keywords
            ):
                excluded_types.add(
                    resource_type
                )

    return excluded_types


def detect_resource_types(question):
    text = normalise_text(question)

    excluded_types = (
        detect_excluded_resource_types(
            question
        )
    )

    requested_types = set()

    for resource_type, keywords in (
        RESOURCE_TYPE_KEYWORDS.items()
    ):

        if resource_type in excluded_types:
            continue

        if any(
            keyword in text
            for keyword in keywords
        ):
            requested_types.add(
                resource_type
            )

    return requested_types


def requires_available_resource(question):
    text = normalise_text(question)

    return (
        "available" in text
        or "currently available" in text
    )


def detect_capacity_requirement(question):
    text = normalise_text(question)

    match = re.search(
        r"for\s+(\d+)\s*(?:people|students)?",
        text
    )

    if match:
        return int(match.group(1))

    return None


def fetch_resources():
    response = requests.get(
        f"{DATABASE_API_URL}/resources",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def select_candidates(resources, question):
    requested_types = detect_resource_types(
        question
    )

    excluded_types = (
        detect_excluded_resource_types(
            question
        )
    )

    require_available = (
        requires_available_resource(
            question
        )
    )

    capacity_required = (
        detect_capacity_requirement(
            question
        )
    )

    candidates = []

    for resource in resources:

        resource_type = resource.get(
            "resource_type"
        )

        status = resource.get(
            "availability_status"
        )

        capacity = resource.get(
            "capacity"
        )

        if resource_type in excluded_types:
            continue

        if (
            requested_types
            and resource_type
            not in requested_types
        ):
            continue

        if (
            require_available
            and status != "Available"
        ):
            continue

        if (
            capacity_required is not None
            and resource_type == "Study Room"
            and (
                capacity is None
                or capacity < capacity_required
            )
        ):
            continue

        candidates.append(resource)

    # Fallback if no specific matches
    if not candidates:

        candidates = [
            resource
            for resource in resources
            if (
                resource.get("resource_type")
                not in excluded_types
            )
        ]

    return candidates[:5]


def build_resource_context(resources):
    lines = []

    for resource in resources:
        lines.append(
            (
                f"Name: {resource.get('resource_name')} | "
                f"Type: {resource.get('resource_type')} | "
                f"Building: {resource.get('building')} | "
                f"Floor: {resource.get('floor')} | "
                f"Capacity: {resource.get('capacity')} | "
                f"Status: {resource.get('availability_status')} | "
                f"Opening Hours: {resource.get('opening_hours')} | "
                f"Location: {resource.get('location')} | "
                f"Description: {resource.get('description')}"
            )
        )

    return "\n".join(lines)


# =========================================================
# AI RECOMMENDATION
# =========================================================

@app.route("/recommend", methods=["POST"])
def recommend_resource():
    data = request.get_json(
        silent=True
    )

    if data is None:
        return jsonify({
            "error": "Request body must contain JSON data"
        }), 400

    question = str(
        data.get(
            "question",
            ""
        )
    ).strip()

    if not question:
        return jsonify({
            "error": "Question is required"
        }), 400

    try:
        resources = fetch_resources()

        candidates = select_candidates(
            resources,
            question
        )

        requested_types = detect_resource_types(
            question
        )

        excluded_types = (
            detect_excluded_resource_types(
                question
            )
        )

        context = build_resource_context(
            candidates
        )

        prompt = f"""
You are a campus resource recommendation assistant.

Only use the candidate resources below.

Do not invent resources or information.

If the user asks for a specific resource type,
recommend only that type.

If the user excludes a resource type,
do not recommend it.

Keep the answer short and clear.

Candidate resources:

{context}

User question:

{question}

Recommendation:
"""

        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        ai_response.raise_for_status()

        ai_data = ai_response.json()

        recommendation = str(
            ai_data.get(
                "response",
                ""
            )
        ).strip()

        return jsonify({
            "question": question,
            "recommendation": recommendation,
            "model": AI_MODEL,
            "resource_count": len(resources),
            "candidate_count": len(candidates),

            "requested_resource_types": sorted(
                requested_types
            ),

            "excluded_resource_types": sorted(
                excluded_types
            ),

            "candidate_resources": [
                {
                    "resource_id":
                        resource.get("resource_id"),

                    "resource_name":
                        resource.get("resource_name"),

                    "resource_type":
                        resource.get("resource_type"),

                    "availability_status":
                        resource.get(
                            "availability_status"
                        )
                }

                for resource in candidates
            ]
        }), 200

    except requests.Timeout as error:
        return jsonify({
            "error": "AI request timed out",
            "details": str(error)
        }), 504

    except requests.RequestException as error:
        return jsonify({
            "error": "AI or database service unavailable",
            "details": str(error)
        }), 503


# =========================================================
# R1 RAG RECOMMENDATION
# =========================================================

@app.get("/api/mcp/resource-count")
def mcp_resource_count():
    """Return the campus resource count through the shared MCP server."""

    outcome = call_mcp_tool(
        "resource_count"
    )

    if not outcome.get("ok"):
        return jsonify({
            "error": outcome.get(
                "error",
                "MCP request failed"
            ),
            "detail": outcome.get("detail"),
        }), outcome.get("status", 502)

    return jsonify({
        "mode": "mcp",
        "tool": "resource_count",
        "result": outcome.get("result"),
    }), 200


@app.get("/api/mcp/resource-by-type/<resource_type>")
def mcp_resource_by_type(resource_type):
    """Return campus resources by type through the shared MCP server."""

    resource_type = resource_type.strip()

    if not resource_type:
        return jsonify({
            "error": "resource_type is required"
        }), 400

    outcome = call_mcp_tool(
        "resource_by_type",
        {
            "resource_type": resource_type
        }
    )

    if not outcome.get("ok"):
        return jsonify({
            "error": outcome.get(
                "error",
                "MCP request failed"
            ),
            "detail": outcome.get("detail"),
        }), outcome.get("status", 502)

    return jsonify({
        "mode": "mcp",
        "tool": "resource_by_type",
        "input": {
            "resource_type": resource_type
        },
        "result": outcome.get("result"),
    }), 200

@app.post("/rag/recommend")
def rag_recommend():
    """Generate a grounded campus resource recommendation using RAG."""

    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json"
        }), 400

    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    question = body.get("question")

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "error": "question is required"
        }), 400

    question = question.strip()

    # Step 1: Retrieve relevant context from the shared RAG server.
    result = retrieve_resource_context(
        question,
        top_k=3,
    )

    if result.get("error"):
        return jsonify(result), 503

    matches = result.get("matches", [])

    # Step 2: Only use sufficiently relevant retrieved context.
    grounded_matches = [
        match
        for match in matches
        if match.get("confidence") in {"high", "medium"}
    ]

    # Step 3: Do not ask the LLM to guess when retrieval is weak.
    if not grounded_matches:
        return jsonify({
            "question": question,
            "mode": "rag",
            "answer": (
                "Insufficient relevant context was found "
                "to answer this question."
            ),
            "model": AI_MODEL,
            "citations": [],
            "confidence": "low",
            "matches": matches,
        }), 200

    context = "\n\n".join(
        match.get("context", "")
        for match in grounded_matches
    )

    citations = list(dict.fromkeys(
        match.get("citation")
        for match in grounded_matches
        if match.get("citation")
    ))

    confidence = (
        "high"
        if any(
            match.get("confidence") == "high"
            for match in grounded_matches
        )
        else "medium"
    )

    prompt = f"""
You are a campus resource recommendation assistant.

Answer the user's question using ONLY the retrieved
campus resource context below.

Do not invent resources, facilities, locations,
opening hours, capacities, or other information.

If the context does not support a claim, do not make it.

Keep the answer short, clear and useful.

Retrieved context:

{context}

User question:

{question}

Grounded answer:
"""

    try:
        # Step 4: Generate an answer grounded in retrieved evidence.
        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )

        ai_response.raise_for_status()

        ai_data = ai_response.json()

        answer = str(
            ai_data.get(
                "response",
                ""
            )
        ).strip()

        if not answer:
            answer = (
                "The retrieved context was relevant, "
                "but no grounded answer was generated."
            )

        # Step 5: Return the answer together with evidence metadata.
        return jsonify({
            "question": question,
            "mode": "rag",
            "answer": answer,
            "model": AI_MODEL,
            "citations": citations,
            "confidence": confidence,
            "matches": matches,
        }), 200

    except requests.Timeout as error:
        return jsonify({
            "error": "AI request timed out",
            "details": str(error),
        }), 504

    except requests.RequestException as error:
        return jsonify({
            "error": "AI service unavailable",
            "details": str(error),
        }), 503

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
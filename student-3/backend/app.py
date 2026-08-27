from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
import requests


app = Flask(__name__)

# Allow Student 3 frontend to call this backend.
CORS(app)


# ---------------------------------------------------------
# Service Configuration
# ---------------------------------------------------------

DATABASE_API_URL = os.getenv(
    "DATABASE_API_URL",
    "http://localhost:5004"
)

AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://localhost:11434/api/generate"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "qwen2.5:0.5b"
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health_check():

    return jsonify({
        "status": "ok",
        "service": "Campus Resource Management Backend API"
    }), 200


# =========================================================
# RESOURCE CRUD PROXY
# =========================================================

@app.route("/resources", methods=["GET"])
def get_resources():

    try:

        params = dict(request.args)

        response = requests.get(
            f"{DATABASE_API_URL}/resources",
            params=params,
            timeout=5
        )

        return jsonify(
            response.json()
        ), response.status_code

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

        return jsonify(
            response.json()
        ), response.status_code

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

        return jsonify(
            response.json()
        ), response.status_code

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

        return jsonify(
            response.json()
        ), response.status_code

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

        return jsonify(
            response.json()
        ), response.status_code

    except requests.RequestException as error:

        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


# =========================================================
# AI RECOMMENDATION HELPERS
# =========================================================

def fetch_current_resources():
    """
    Retrieve the latest campus resources from
    the Student 3 database service.
    """

    response = requests.get(
        f"{DATABASE_API_URL}/resources",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def normalise_text(text):
    """
    Convert text to lowercase and remove unnecessary
    punctuation to make keyword analysis easier.
    """

    if not text:
        return ""

    return re.sub(
        r"[^a-z0-9\s]",
        " ",
        str(text).lower()
    )


# ---------------------------------------------------------
# Detect Resource Type
# ---------------------------------------------------------

def detect_resource_types(question):
    """
    Detect which campus resource types the user
    appears to be requesting.
    """

    text = normalise_text(question)

    requested_types = set()

    # Printer intent
    if any(
        keyword in text
        for keyword in [
            "printer",
            "printing",
            "print",
            "photocopy",
            "photocopying"
        ]
    ):
        requested_types.add("Printer")

    # Computer Lab intent
    if any(
        keyword in text
        for keyword in [
            "computer lab",
            "computer",
            "desktop",
            "pc",
            "lab"
        ]
    ):
        requested_types.add("Computer Lab")

    # Library intent
    if any(
        keyword in text
        for keyword in [
            "library",
            "books",
            "reading"
        ]
    ):
        requested_types.add("Library")

    # Study space intent
    if any(
        keyword in text
        for keyword in [
            "study room",
            "study space",
            "quiet",
            "study",
            "group room",
            "meeting room"
        ]
    ):
        requested_types.add("Study Room")

        # Libraries can also be suitable for general
        # quiet study requests.
        requested_types.add("Library")

    # Parking intent
    if any(
        keyword in text
        for keyword in [
            "parking",
            "park my car",
            "car park"
        ]
    ):
        requested_types.add("Parking")

    return requested_types


# ---------------------------------------------------------
# Detect Availability Requirement
# ---------------------------------------------------------

def requires_available_resource(question):
    """
    Detect whether the user explicitly asks
    for something currently available/open/free.
    """

    text = normalise_text(question)

    availability_words = [
        "available",
        "free",
        "open now",
        "currently open",
        "currently available",
        "not busy"
    ]

    return any(
        keyword in text
        for keyword in availability_words
    )


# ---------------------------------------------------------
# Detect Capacity Requirement
# ---------------------------------------------------------

def detect_capacity_requirement(question):
    """
    Detect requests such as:
    - room for 6
    - space for 10 people
    - 5 people
    """

    text = normalise_text(question)

    patterns = [
        r"for\s+(\d+)\s*(?:people|persons|students)?",
        r"(\d+)\s*(?:people|persons|students)",
        r"group\s+of\s+(\d+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            try:
                return int(
                    match.group(1)
                )

            except ValueError:
                pass

    return None


# ---------------------------------------------------------
# Detect Quiet Preference
# ---------------------------------------------------------

def requires_quiet_space(question):

    text = normalise_text(question)

    quiet_words = [
        "quiet",
        "silent",
        "peaceful",
        "individual study",
        "focus",
        "concentrate"
    ]

    return any(
        keyword in text
        for keyword in quiet_words
    )


# ---------------------------------------------------------
# Score Resource
# ---------------------------------------------------------

def score_resource(
    resource,
    requested_types,
    availability_required,
    capacity_required,
    quiet_required
):
    """
    Give each resource a deterministic relevance score.

    Python handles factual matching.
    Qwen only explains the final candidates.
    """

    score = 0

    resource_type = (
        resource.get("resource_type")
        or ""
    )

    status = (
        resource.get("availability_status")
        or ""
    )

    capacity = (
        resource.get("capacity")
    )

    description = normalise_text(
        resource.get("description")
    )

    resource_name = normalise_text(
        resource.get("resource_name")
    )


    # ---------------------------------------------
    # Type matching
    # ---------------------------------------------

    if requested_types:

        if resource_type in requested_types:
            score += 50

        else:
            # Strong penalty prevents a Printer being
            # recommended for a Computer Lab request.
            score -= 100


    # ---------------------------------------------
    # Availability
    # ---------------------------------------------

    if status == "Available":
        score += 20

    elif status == "Busy":
        score -= 5

    elif status in [
        "Unavailable",
        "Closed"
    ]:
        score -= 30


    if (
        availability_required
        and status != "Available"
    ):
        score -= 100


    # ---------------------------------------------
    # Capacity
    # ---------------------------------------------

    if capacity_required is not None:

        if (
            capacity is not None
            and capacity >= capacity_required
        ):
            score += 20

            # Prefer a capacity reasonably close
            # to the user's requirement.
            difference = (
                capacity - capacity_required
            )

            score += max(
                0,
                10 - difference
            )

        else:
            score -= 100


    # ---------------------------------------------
    # Quiet preference
    # ---------------------------------------------

    if quiet_required:

        quiet_text = (
            resource_name
            + " "
            + description
        )

        if any(
            word in quiet_text
            for word in [
                "quiet",
                "individual",
                "library",
                "study"
            ]
        ):
            score += 15


    return score


# ---------------------------------------------------------
# Select Candidate Resources
# ---------------------------------------------------------

def select_candidate_resources(
    resources,
    question
):
    """
    Analyse the question and return only resources
    that are realistically relevant.
    """

    requested_types = detect_resource_types(
        question
    )

    availability_required = (
        requires_available_resource(
            question
        )
    )

    capacity_required = (
        detect_capacity_requirement(
            question
        )
    )

    quiet_required = (
        requires_quiet_space(
            question
        )
    )


    scored_resources = []


    for resource in resources:

        score = score_resource(
            resource,
            requested_types,
            availability_required,
            capacity_required,
            quiet_required
        )

        scored_resources.append(
            (
                score,
                resource
            )
        )


    # Highest score first.
    scored_resources.sort(
        key=lambda item: item[0],
        reverse=True
    )


    # Only keep candidates that are relevant.
    candidates = [
        resource
        for score, resource
        in scored_resources
        if score >= 0
    ]


    # If filters became too restrictive,
    # fall back to highest-ranked available resources.
    if not candidates:

        available_resources = [
            resource
            for resource in resources
            if (
                resource.get(
                    "availability_status"
                )
                == "Available"
            )
        ]

        candidates = (
            available_resources
            if available_resources
            else resources
        )


    # Limit prompt size and reduce AI confusion.
    return candidates[:5]


# ---------------------------------------------------------
# Convert Resources to AI Context
# ---------------------------------------------------------

def build_resource_context(resources):
    """
    Convert only the selected candidate resources
    into structured text for Qwen.
    """

    context_lines = []

    for resource in resources:

        context_lines.append(
            (
                f"Resource ID: "
                f"{resource.get('resource_id')}\n"

                f"Name: "
                f"{resource.get('resource_name')}\n"

                f"Type: "
                f"{resource.get('resource_type')}\n"

                f"Building: "
                f"{resource.get('building')}\n"

                f"Floor: "
                f"{resource.get('floor') or 'N/A'}\n"

                f"Capacity: "
                f"{resource.get('capacity') if resource.get('capacity') is not None else 'N/A'}\n"

                f"Status: "
                f"{resource.get('availability_status')}\n"

                f"Opening Hours: "
                f"{resource.get('opening_hours') or 'N/A'}\n"

                f"Location: "
                f"{resource.get('location') or 'N/A'}\n"

                f"Description: "
                f"{resource.get('description') or 'N/A'}\n"
            )
        )

    return "\n---\n".join(
        context_lines
    )


# =========================================================
# AI RECOMMENDATION ENDPOINT
# =========================================================

@app.route("/recommend", methods=["POST"])
def recommend_resource():

    data = request.get_json(
        silent=True
    )


    # No JSON body.
    if data is None:

        return jsonify({
            "error":
                "Request body must contain JSON data"
        }), 400


    question = str(
        data.get(
            "question",
            ""
        )
    ).strip()


    # JSON exists but question is missing.
    if not question:

        return jsonify({
            "error": "Question is required"
        }), 400


    try:

        # -------------------------------------------------
        # ACT
        #
        # Retrieve latest resource records.
        # -------------------------------------------------

        resources = (
            fetch_current_resources()
        )


        if not resources:

            return jsonify({
                "error":
                    "No campus resources are currently available"
            }), 404


        # -------------------------------------------------
        # Python candidate filtering
        # -------------------------------------------------

        candidates = (
            select_candidate_resources(
                resources,
                question
            )
        )


        resource_context = (
            build_resource_context(
                candidates
            )
        )


        # -------------------------------------------------
        # Grounded AI Prompt
        # -------------------------------------------------

        prompt = f"""
You are Campus AI, a university campus resource
recommendation assistant.

IMPORTANT RULES:

You may ONLY recommend resources listed in
CANDIDATE RESOURCES below.

The candidates have already been filtered by the
backend using the user's requirements.

Do NOT recommend any other campus resource.

Do NOT invent:
- resource names
- locations
- opening hours
- capacities
- availability
- facilities
- services

Use only facts explicitly shown in the candidate data.

If a resource is marked Busy, Closed or Unavailable,
do not describe it as Available.

If the user asks for a particular resource type,
only recommend that resource type from the candidate list.

Recommend the best 1 to 3 resources.

For each recommendation:
- state the exact resource name
- briefly explain why it matches the request
- mention useful facts such as status, capacity,
  location or opening hours when relevant

Keep the answer concise and student-friendly.

CANDIDATE RESOURCES:

{resource_context}

USER REQUEST:

{question}

Give the grounded recommendation now.
"""


        # -------------------------------------------------
        # Shared Ollama / Qwen
        # -------------------------------------------------

        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False,

                # Lower temperature makes the small
                # model less creative and more factual.
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=60
        )


        ai_response.raise_for_status()


        ai_data = (
            ai_response.json()
        )


        recommendation = str(
            ai_data.get(
                "response",
                ""
            )
        ).strip()


        if not recommendation:

            return jsonify({
                "error":
                    "AI service returned an empty response"
            }), 502


        # -------------------------------------------------
        # Return useful evidence metadata as well.
        # -------------------------------------------------

        return jsonify({

            "question":
                question,

            "recommendation":
                recommendation,

            "model":
                AI_MODEL,

            "resource_count":
                len(resources),

            "candidate_count":
                len(candidates),

            "candidate_resources": [
                {
                    "resource_id":
                        resource.get(
                            "resource_id"
                        ),

                    "resource_name":
                        resource.get(
                            "resource_name"
                        ),

                    "resource_type":
                        resource.get(
                            "resource_type"
                        ),

                    "availability_status":
                        resource.get(
                            "availability_status"
                        )
                }

                for resource
                in candidates
            ]

        }), 200


    except requests.Timeout as error:

        return jsonify({
            "error":
                "AI recommendation request timed out",
            "details":
                str(error)
        }), 504


    except requests.RequestException as error:

        return jsonify({
            "error":
                "AI or database service unavailable",
            "details":
                str(error)
        }), 503


    except Exception as error:

        return jsonify({
            "error":
                "Unexpected recommendation error",
            "details":
                str(error)
        }), 500


# =========================================================
# START BACKEND
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
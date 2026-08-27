from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
import requests


app = Flask(__name__)

CORS(app)


# =========================================================
# SERVICE CONFIGURATION
# =========================================================

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
# HEALTH
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

        response = requests.get(
            f"{DATABASE_API_URL}/resources",
            params=dict(request.args),
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
# AI HELPERS
# =========================================================

def fetch_current_resources():

    response = requests.get(
        f"{DATABASE_API_URL}/resources",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def normalise_text(text):

    if not text:
        return ""

    return re.sub(
        r"[^a-z0-9\s]",
        " ",
        str(text).lower()
    )


# =========================================================
# RESOURCE TYPE DEFINITIONS
# =========================================================

RESOURCE_TYPE_KEYWORDS = {
    "Printer": [
        "printer",
        "printing",
        "print",
        "photocopy",
        "photocopying"
    ],

    "Computer Lab": [
        "computer lab",
        "computer",
        "desktop",
        "pc",
        "lab"
    ],

    "Library": [
        "library",
        "books",
        "reading"
    ],

    "Study Room": [
        "study room",
        "study space",
        "quiet",
        "study",
        "group room",
        "meeting room"
    ],

    "Parking": [
        "parking",
        "park my car",
        "car park"
    ]
}


# =========================================================
# EXCLUSION / NEGATION DETECTION v0.3
# =========================================================

def detect_excluded_resource_types(question):
    """
    Detect resource types explicitly rejected by the user.

    Examples:
    - not a printer
    - not a library
    - do not recommend study rooms
    - don't recommend parking
    - without printers
    - no study rooms
    """

    text = normalise_text(question)

    excluded_types = set()


    exclusion_patterns = [
        "not a {keyword}",
        "not an {keyword}",
        "not {keyword}",
        "no {keyword}",
        "without {keyword}",
        "do not recommend {keyword}",
        "dont recommend {keyword}",
        "do not want {keyword}",
        "dont want {keyword}",
        "exclude {keyword}",
        "avoid {keyword}"
    ]


    for resource_type, keywords in (
        RESOURCE_TYPE_KEYWORDS.items()
    ):

        for keyword in keywords:

            for pattern in exclusion_patterns:

                phrase = pattern.format(
                    keyword=keyword
                )

                if phrase in text:

                    excluded_types.add(
                        resource_type
                    )

                    break


            if resource_type in excluded_types:
                break


    return excluded_types


# =========================================================
# POSITIVE TYPE DETECTION
# =========================================================

def detect_resource_types(question):
    """
    Detect positively requested resource types.

    v0.3 ignores resource types that occur only inside
    negated phrases.
    """

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


    # General study request can reasonably include
    # Library as well as Study Room.
    if (
        "Study Room" in requested_types
        and "Library" not in excluded_types
    ):

        if any(
            phrase in text
            for phrase in [
                "quiet",
                "study",
                "study space",
                "place to study"
            ]
        ):

            requested_types.add(
                "Library"
            )


    return requested_types


# =========================================================
# OTHER REQUIREMENT DETECTION
# =========================================================

def requires_available_resource(question):

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


def detect_capacity_requirement(question):

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


# =========================================================
# RESOURCE SCORING
# =========================================================

def score_resource(
    resource,
    requested_types,
    excluded_types,
    availability_required,
    capacity_required,
    quiet_required
):

    score = 0


    resource_type = (
        resource.get(
            "resource_type"
        )
        or ""
    )

    status = (
        resource.get(
            "availability_status"
        )
        or ""
    )

    capacity = resource.get(
        "capacity"
    )

    description = normalise_text(
        resource.get(
            "description"
        )
    )

    resource_name = normalise_text(
        resource.get(
            "resource_name"
        )
    )


    # -----------------------------------------------------
    # EXPLICIT EXCLUSION
    # -----------------------------------------------------

    if resource_type in excluded_types:

        return -1000


    # -----------------------------------------------------
    # TYPE MATCH
    # -----------------------------------------------------

    if requested_types:

        if resource_type in requested_types:

            score += 50

        else:

            score -= 100


    # -----------------------------------------------------
    # AVAILABILITY
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # CAPACITY
    # -----------------------------------------------------

    if capacity_required is not None:

        if (
            capacity is not None
            and capacity >= capacity_required
        ):

            score += 20


            difference = (
                capacity
                - capacity_required
            )


            score += max(
                0,
                10 - difference
            )

        else:

            score -= 100


    # -----------------------------------------------------
    # QUIET PREFERENCE
    # -----------------------------------------------------

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


# =========================================================
# CANDIDATE SELECTION
# =========================================================

def select_candidate_resources(
    resources,
    question
):

    requested_types = (
        detect_resource_types(
            question
        )
    )

    excluded_types = (
        detect_excluded_resource_types(
            question
        )
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
            excluded_types,
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


    scored_resources.sort(
        key=lambda item: item[0],
        reverse=True
    )


    candidates = [
        resource
        for score, resource
        in scored_resources
        if score >= 0
    ]


    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    if not candidates:

        available_resources = [
            resource
            for resource in resources
            if (
                resource.get(
                    "availability_status"
                )
                == "Available"
                and
                resource.get(
                    "resource_type"
                )
                not in excluded_types
            )
        ]


        candidates = (
            available_resources
            if available_resources
            else [
                resource
                for resource in resources
                if resource.get(
                    "resource_type"
                )
                not in excluded_types
            ]
        )


    return candidates[:5]


# =========================================================
# AI CONTEXT
# =========================================================

def build_resource_context(resources):

    context_lines = []


    for resource in resources:

        capacity = (
            resource.get(
                "capacity"
            )
        )


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
                f"{capacity if capacity is not None else 'N/A'}\n"

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
# RECOMMEND ENDPOINT
# =========================================================

@app.route("/recommend", methods=["POST"])
def recommend_resource():

    data = request.get_json(
        silent=True
    )


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


    if not question:

        return jsonify({
            "error":
                "Question is required"
        }), 400


    try:

        resources = (
            fetch_current_resources()
        )


        if not resources:

            return jsonify({
                "error":
                    "No campus resources are currently available"
            }), 404


        requested_types = (
            detect_resource_types(
                question
            )
        )

        excluded_types = (
            detect_excluded_resource_types(
                question
            )
        )


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


        requested_text = (
            ", ".join(
                sorted(
                    requested_types
                )
            )
            if requested_types
            else
            "No specific type detected"
        )


        excluded_text = (
            ", ".join(
                sorted(
                    excluded_types
                )
            )
            if excluded_types
            else
            "None"
        )


        prompt = f"""
You are Campus AI, a university campus resource
recommendation assistant.

The backend has already analysed the user's request.

POSITIVE RESOURCE TYPES:
{requested_text}

EXCLUDED RESOURCE TYPES:
{excluded_text}

IMPORTANT RULES:

1. You may ONLY recommend resources from
   CANDIDATE RESOURCES below.

2. Never recommend a resource whose type appears
   in EXCLUDED RESOURCE TYPES.

3. Do not invent:
   - resource names
   - locations
   - opening hours
   - capacities
   - availability
   - facilities
   - services

4. Use only facts explicitly provided in
   CANDIDATE RESOURCES.

5. If the user asks for a specific resource type,
   recommend only that type.

6. If the user explicitly rejects a resource type,
   never recommend it.

7. If a resource is Busy, Closed or Unavailable,
   do not describe it as Available.

8. Recommend the best 1 to 3 resources.

9. Keep the response concise and student-friendly.

CANDIDATE RESOURCES:

{resource_context}

USER REQUEST:

{question}

Give the grounded recommendation now.
"""


        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False,

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

            "requested_resource_types":
                sorted(
                    requested_types
                ),

            "excluded_resource_types":
                sorted(
                    excluded_types
                ),

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
# START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
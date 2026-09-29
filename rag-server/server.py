from flask import Flask, jsonify, request

from retrievers.student1_course_retriever import (
    retrieve_course_context,
)

from retrievers.student2_assignment_retriever import (
    retrieve_assignment_context,
)

from retrievers.student4_event_retriever import (
    retrieve_event_context,
)


app = Flask(__name__)


@app.get("/health")
def health():

    return jsonify({
        "service": "Smart Campus RAG Server",
        "status": "ok",
    })


@app.post("/retrieve/course")
def retrieve_course():

    if not request.is_json:

        return jsonify({
            "error": (
                "Content-Type must be "
                "application/json"
            ),
        }), 400

    body = request.get_json(
        silent=True
    )

    if not isinstance(
        body,
        dict
    ):

        return jsonify({
            "error": (
                "Request body must be "
                "a JSON object"
            ),
        }), 400

    try:

        result = retrieve_course_context(
            body.get("query"),
            body.get("top_k", 3),
        )

    except Exception:

        return jsonify({
            "error": "RAG server error"
        }), 500

    return jsonify(
        result
    )

@app.post("/retrieve/assignment")
def retrieve_assignment():

    if not request.is_json:

        return jsonify({
            "error": (
                "Content-Type must be "
                "application/json"
            ),
        }), 400

    body = request.get_json(
        silent=True
    )

    if not isinstance(
        body,
        dict
    ):

        return jsonify({
            "error": (
                "Request body must be "
                "a JSON object"
            ),
        }), 400

    try:

        result = retrieve_assignment_context(
            body.get("query"),
            body.get("top_k", 3),
        )

    except Exception:

        return jsonify({
            "error": "RAG server error"
        }), 500

    return jsonify(
        result
    )

@app.post("/retrieve/resource")
def retrieve_resource():

    if not request.is_json:

        return jsonify({
            "error": (
                "Content-Type must be "
                "application/json"
            ),
        }), 400

    body = request.get_json(
        silent=True
    )

    if not isinstance(
        body,
        dict
    ):

        return jsonify({
            "error": (
                "Request body must be "
                "a JSON object"
            ),
        }), 400

    try:

        # Student 3's optional embedding stack must not block course retrieval.
        from retrievers.student3_resource_retriever import retrieve_resource_context

        result = retrieve_resource_context(
            body.get("query"),
            body.get("top_k", 3),
        )

    except Exception:

        return jsonify({
            "error": "RAG server error"
        }), 500

    return jsonify(
        result
    )


@app.post("/retrieve/event")
def retrieve_event():

    if not request.is_json:

        return jsonify({
            "error": (
                "Content-Type must be "
                "application/json"
            ),
        }), 400

    body = request.get_json(
        silent=True
    )

    if not isinstance(
        body,
        dict
    ):

        return jsonify({
            "error": (
                "Request body must be "
                "a JSON object"
            ),
        }), 400

    try:

        result = retrieve_event_context(
            body.get("query"),
            body.get("top_k", 3),
        )

    except Exception:

        return jsonify({
            "error": "RAG server error"
        }), 500

    return jsonify(
        result
    )


if __name__ == "__main__":

    print(
        "Starting Smart Campus RAG Server...",
        flush=True
    )

    print(
        "Server status: RUNNING",
        flush=True
    )

    print(
        "Course RAG endpoint: "
        "http://localhost:9101/retrieve/course",
        flush=True
    )

    print(
    "Assignment RAG endpoint: "
    "http://localhost:9101/retrieve/assignment",
    flush=True
)

    print(
        "Resource RAG endpoint: "
        "http://localhost:9101/retrieve/resource",
        flush=True
    )

    print(
        "Event RAG endpoint: "
        "http://localhost:9101/retrieve/event",
        flush=True
    )

    app.run(
        host="0.0.0.0",
        port=9101
    )

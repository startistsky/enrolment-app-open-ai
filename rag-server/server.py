from flask import Flask, jsonify, request

from retrievers.student1_course_retriever import (
    retrieve_course_context,
)

from retrievers.student4_event_retriever import (
    retrieve_event_context,
)

from retrievers.student5_career_retriever import (
    retrieve_career_context,
    index_knowledge, 
    rag_status
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

# student 5 Career RAG 
@app.post("/retrieve/career")
def retrieve_career():

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

    query = body.get(
        "query"
    )

    if not query:

        return jsonify({
            "error": "Query is required"
        }), 400

    try:

        top_k = body.get(
            "top_k",
            4
        )

        result = retrieve_career_context(
            query,
            top_k
        )

    except Exception as error:

        print(
            "CAREER RAG ERROR:",
            repr(error),
            flush=True
        )

        return jsonify({
            "error": "RAG server error"
        }), 500

    return jsonify(
        result
    )

# Student 5 check RAG index and status 
@app.get("/status")
def status():
    return jsonify(
        rag_status()
    )

@app.post("/index/career")
def index_career():

    try:

        result = index_knowledge()

        return jsonify(
            result
        )

    except Exception as error:

        print(
            "CAREER RAG INDEX ERROR:",
            repr(error),
            flush=True
        )

        return jsonify({
            "success": False,
            "error": "RAG indexing failed"
        }), 500

# main
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
        "Event RAG endpoint: "
        "http://localhost:9101/retrieve/event",
        flush=True
    )

    print(
        "Career RAG endpoint: "
        "http://localhost:9101/retrieve/career",
        flush=True
    )

    app.run(
        host="0.0.0.0",
        port=9101
    )
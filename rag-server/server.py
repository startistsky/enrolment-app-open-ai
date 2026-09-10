from flask import Flask, jsonify, request

from retrievers.student1_course_retriever import retrieve_course_context


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
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "error": "Request body must be a JSON object",
        }), 400

    try:
        result = retrieve_course_context(
            body.get("query"),
            body.get("top_k", 3),
        )
    except Exception:
        return jsonify({"error": "RAG server error"}), 500

    return jsonify(result)


if __name__ == "__main__":
    print("Starting Smart Campus RAG Server...", flush=True)
    print("Server status: RUNNING", flush=True)
    print(
        "RAG endpoint: http://localhost:9101/retrieve/course",
        flush=True,
    )
    app.run(host="0.0.0.0", port=9101)

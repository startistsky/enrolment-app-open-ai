import os
from flask import Flask, jsonify, request

from ai import ai_bp
from events import events_bp
from multi_agent import multi_agent_bp

app = Flask(__name__)

app.register_blueprint(ai_bp)
app.register_blueprint(events_bp)
app.register_blueprint(multi_agent_bp)

@app.before_request
def cloud_ai_guard():
    if os.getenv("AI_SERVICES_ENABLED", "true").lower() == "false" and (
        request.blueprint == "ai"
    ):
        return jsonify(error="AI, MCP, RAG and Multi-Agent services are disabled in this deployment"), 503


@app.get("/health")
def health():
    return {
        "status": "backend is running"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true"
    )
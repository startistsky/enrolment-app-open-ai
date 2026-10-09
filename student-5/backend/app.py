import os
from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

from flask_cors import CORS

from model.database import init_db

from model.seed import seed

from crud.service import service

from agent.ai_routes import ai_routes


app = Flask(

    __name__,

    template_folder="../frontend/templates",

    static_folder="../frontend",

    static_url_path="/static"
)

CORS(app)

# initialise database
init_db()
# seed data 
seed()

# health check
@app.before_request
def cloud_ai_guard():
    if os.getenv("AI_SERVICES_ENABLED", "true").lower() == "false" and (
        request.blueprint == "ai_routes"
    ):
        return jsonify(error="AI, MCP, RAG and Multi-Agent services are disabled in this deployment"), 503


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
    "status": "healthy"
}), 200

# render frontend 
@app.route("/")
def index():

    return render_template(
        "index.html"
    )

@app.route("/job.html")
def job_page():

    return render_template(
        "job.html"
    )


@app.route("/dashboard.html")
def dashboard_page():

    return render_template(
        "dashboard.html"
    )


@app.route("/admin.html")
def admin_page():

    return render_template(
        "admin.html"
    )


# API routes
app.register_blueprint(
    service,
    url_prefix="/api"
)

app.register_blueprint(
    ai_routes,
    url_prefix="/api"
)

# run 
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8005,
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true"
    )

    #     app.run(
    #     host="127.0.0.1",
    #     port=5005,
    #     debug=True
    # )
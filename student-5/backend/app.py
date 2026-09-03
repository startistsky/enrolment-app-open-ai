from flask import (
    Flask,
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
        debug=True
    )

    #     app.run(
    #     host="127.0.0.1",
    #     port=5005,
    #     debug=True
    # )
from flask import (
    Flask,
    render_template
)

from flask_cors import CORS

from database import init_db

from service import service

from ai_routes import ai_routes


app = Flask(

    __name__,

    template_folder="../frontend/templates",

    static_folder="../frontend",

    static_url_path="/static"
)

CORS(app)

init_db()


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
        host="127.0.0.1",
        port=5005,
        debug=True
    )
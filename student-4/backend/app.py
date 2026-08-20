from flask import Flask, send_from_directory
import os
from ai import ai_bp
from events import events_bp


app = Flask(__name__)


# Register Blueprints
app.register_blueprint(ai_bp)
app.register_blueprint(events_bp)

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "../frontend"
)

SHARED_CSS_DIR = os.path.join(
    BASE_DIR,
    "../../shared/frontend/css"
)

# Frontend routes

@app.route("/shared/css/<path:filename>")
def shared_css(filename):
    return send_from_directory(
        SHARED_CSS_DIR,
        filename
    )


@app.route("/")
def home():
    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/js/<path:filename>")
def frontend_js(filename):
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "js"),
        filename
    )



# Application entry point
if __name__ == "__main__":
    app.run(
        debug=True,
        port=8000
    )
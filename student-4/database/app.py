import os
from flask import Flask
from event_controller import event_bp

app = Flask(__name__)

app.register_blueprint(event_bp)


@app.get("/health")
def health():
    return {
        "status": "database-service is running"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true"
    )
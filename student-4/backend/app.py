from flask import Flask

from ai import ai_bp
from events import events_bp


app = Flask(__name__)

app.register_blueprint(ai_bp)
app.register_blueprint(events_bp)


@app.get("/health")
def health():
    return {
        "status": "backend is running"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )

import os
import sys
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)
sys.path.insert(0, BACKEND_DIR)

from app import app


def test_backend_health():
    """Backend health endpoint should work."""
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "backend is running"


def test_ai_disabled_by_environment():
    """Check the current AI service guard behavior."""
    app.config["TESTING"] = True

    with patch.dict(os.environ, {"AI_SERVICES_ENABLED": "false"}):
        with app.test_client() as client:
            response = client.post(
                "/api/ai",
                json={"message": "Hello"}
            )

    assert response.status_code == 503
    assert "disabled" in response.get_json()["error"]

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests


app = Flask(__name__)

# Allow the frontend running on localhost:8083
# to access this backend API.
CORS(app)


DATABASE_API_URL = os.getenv(
    "DATABASE_API_URL",
    "http://localhost:5004"
)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "Campus Resource Management Backend API"
    }), 200


@app.route("/resources", methods=["GET"])
def get_resources():
    try:
        params = dict(request.args)

        response = requests.get(
            f"{DATABASE_API_URL}/resources",
            params=params,
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    try:
        response = requests.get(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources", methods=["POST"])
def create_resource():
    try:
        response = requests.post(
            f"{DATABASE_API_URL}/resources",
            json=request.get_json(),
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    try:
        response = requests.put(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            json=request.get_json(),
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


@app.route("/resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    try:
        response = requests.delete(
            f"{DATABASE_API_URL}/resources/{resource_id}",
            timeout=5
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException as error:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(error)
        }), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
from flask import Blueprint, jsonify, request

from event_db import (
    get_all_events,
    create_event as create_event_db,
    update_event as update_event_db,
    delete_event as delete_event_db,
)


events_bp = Blueprint("events", __name__)


@events_bp.route("/api/events", methods=["GET"])
def get_events():
    events = get_all_events()

    return jsonify(events)


@events_bp.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json() or {}

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    date = data.get("date", "").strip()
    location = data.get("location", "").strip()
    description = data.get("description", "").strip()

    if not title or not category or not date or not location or not description:
        return jsonify({
            "error": "All required fields must be provided."
        }), 400

    event_id = create_event_db(
        title,
        category,
        date,
        location,
        description
    )

    return jsonify({
        "message": "Event created successfully.",
        "id": event_id
    }), 201


@events_bp.route("/api/events/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    data = request.get_json() or {}

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    date = data.get("date", "").strip()
    location = data.get("location", "").strip()
    description = data.get("description", "").strip()

    if not title or not category or not date or not location or not description:
        return jsonify({
            "error": "All required fields must be provided."
        }), 400

    updated = update_event_db(
        event_id,
        title,
        category,
        date,
        location,
        description
    )

    if not updated:
        return jsonify({
            "error": "Event not found."
        }), 404

    return jsonify({
        "message": "Event updated successfully."
    }), 200


@events_bp.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    deleted = delete_event_db(event_id)

    if not deleted:
        return jsonify({
            "error": "Event not found."
        }), 404

    return jsonify({
        "message": "Event deleted successfully."
    }), 200
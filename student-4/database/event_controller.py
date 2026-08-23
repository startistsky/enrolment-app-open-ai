from flask import Blueprint, jsonify, request

from event_repository import (
    get_events,
    create_event,
    update_event,
    delete_event,
)

event_bp = Blueprint("events", __name__)


@event_bp.get("/events")
def get_all():
    return jsonify(get_events())


@event_bp.post("/events")
def create():
    data = request.get_json()

    event_id = create_event(
        data["title"],
        data["category"],
        data["date"],
        data["location"],
        data["description"],
        data.get("emoji", ""),
    )

    return jsonify({"id": event_id}), 201


@event_bp.put("/events/<int:event_id>")
def update(event_id):
    data = request.get_json()

    updated = update_event(
        event_id,
        data["title"],
        data["category"],
        data["date"],
        data["location"],
        data["description"],
        data.get("emoji", ""),
    )

    if not updated:
        return jsonify({"error": "Event not found"}), 404

    return jsonify({"status": "updated"})


@event_bp.delete("/events/<int:event_id>")
def delete(event_id):
    deleted = delete_event(event_id)

    if not deleted:
        return jsonify({"error": "Event not found"}), 404

    return jsonify({"status": "deleted"})
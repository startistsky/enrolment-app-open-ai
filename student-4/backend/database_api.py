import os
import requests


DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://database:5002"
)


def get_events():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/events",
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def create_event(title, category, date, location, description):
    response = requests.post(
        f"{DATABASE_SERVICE_URL}/events",
        json={
            "title": title,
            "category": category,
            "date": date,
            "location": location,
            "description": description,
        },
        timeout=10
    )
    response.raise_for_status()
    return response.json()["id"]


def update_event(
    event_id,
    title,
    category,
    date,
    location,
    description
):
    response = requests.put(
        f"{DATABASE_SERVICE_URL}/events/{event_id}",
        json={
            "title": title,
            "category": category,
            "date": date,
            "location": location,
            "description": description,
        },
        timeout=10
    )

    if response.status_code == 404:
        return False

    response.raise_for_status()
    return True


def delete_event(event_id):
    response = requests.delete(
        f"{DATABASE_SERVICE_URL}/events/{event_id}",
        timeout=10
    )

    if response.status_code == 404:
        return False

    response.raise_for_status()
    return True
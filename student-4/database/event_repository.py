import os
import sqlite3


DATABASE = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "events.db")
)


def get_events():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM events").fetchall()
        return [dict(row) for row in rows]


def create_event(title, category, date, location, description):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (title, category, date, location, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, category, date, location, description),
        )
        return cursor.lastrowid


def update_event(event_id, title, category, date, location, description):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            """
            UPDATE events
            SET title = ?, category = ?, date = ?, location = ?, description = ?
            WHERE id = ?
            """,
            (title, category, date, location, description, event_id),
        )
        return cursor.rowcount > 0


def delete_event(event_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "DELETE FROM events WHERE id = ?",
            (event_id,),
        )
        return cursor.rowcount > 0
import sqlite3
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "../database/events.db"
)


def get_all_events():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")

    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]


def create_event(
    title,
    category,
    date,
    location,
    description
):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO events (
            title,
            category,
            date,
            location,
            description
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            title,
            category,
            date,
            location,
            description,
        ),
    )

    event_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return event_id


def update_event(
    event_id,
    title,
    category,
    date,
    location,
    description
):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE events
        SET
            title = ?,
            category = ?,
            date = ?,
            location = ?,
            description = ?
        WHERE id = ?
        """,
        (
            title,
            category,
            date,
            location,
            description,
            event_id,
        ),
    )

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


def delete_event(event_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,),
    )

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted

def get_events_for_ai():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, date, category, location, description
        FROM events
    """)

    events = cursor.fetchall()

    conn.close()

    return events
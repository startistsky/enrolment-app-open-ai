import os
import sqlite3
from pathlib import Path


# ---------------------------------------------------------
# Database Path
# ---------------------------------------------------------

# Docker:
# DATABASE_PATH=/data/campus_resources.db
#
# Local development:
# student-3/database/campus_resources.db

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent
    / "campus_resources.db"
)

DB_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(DEFAULT_DB_PATH)
    )
)


# ---------------------------------------------------------
# Seed Data
# ---------------------------------------------------------

RESOURCES = [
    (
        "UTS Library",
        "Library",
        "UTS Central",
        "Levels 7-9",
        500,
        "Available",
        "8:00 AM - 10:00 PM",
        "Building 2",
        "Library with quiet study areas, computers and group study spaces."
    ),
    (
        "Building 11 Study Room 1",
        "Study Room",
        "Building 11",
        "Level 4",
        6,
        "Available",
        "8:00 AM - 9:00 PM",
        "Building 11, Level 4",
        "Small group study room suitable for collaborative work."
    ),
    (
        "Building 11 Study Room 2",
        "Study Room",
        "Building 11",
        "Level 4",
        8,
        "Busy",
        "8:00 AM - 9:00 PM",
        "Building 11, Level 4",
        "Group study room with a whiteboard and display screen."
    ),
    (
        "Building 10 Computer Lab",
        "Computer Lab",
        "Building 10",
        "Level 3",
        30,
        "Available",
        "8:00 AM - 8:00 PM",
        "Building 10, Level 3",
        "Computer laboratory with desktop computers and study workstations."
    ),
    (
        "UTS Central Computer Lab",
        "Computer Lab",
        "UTS Central",
        "Level 5",
        40,
        "Available",
        "8:00 AM - 10:00 PM",
        "Building 2, Level 5",
        "Large computer laboratory available for individual study."
    ),
    (
        "Building 2 Printer",
        "Printer",
        "UTS Central",
        "Level 7",
        1,
        "Available",
        "8:00 AM - 10:00 PM",
        "Building 2, Level 7",
        "Colour and black-and-white printing service near the library."
    ),
    (
        "Building 11 Printer",
        "Printer",
        "Building 11",
        "Level 2",
        1,
        "Available",
        "8:00 AM - 9:00 PM",
        "Building 11, Level 2",
        "Student printer supporting colour and black-and-white printing."
    ),
    (
        "Building 1 Quiet Study Area",
        "Study Room",
        "Building 1",
        "Level 3",
        20,
        "Available",
        "8:00 AM - 8:00 PM",
        "Building 1, Level 3",
        "Quiet study area designed for individual study and reading."
    ),
    (
        "Building 6 Study Space",
        "Study Room",
        "Building 6",
        "Level 4",
        15,
        "Busy",
        "9:00 AM - 7:00 PM",
        "Building 6, Level 4",
        "Open study space with tables and power outlets."
    ),
    (
        "Thomas Street Parking",
        "Parking",
        "Building 10",
        "Ground",
        50,
        "Available",
        "6:00 AM - 11:00 PM",
        "Thomas Street",
        "Parking facility close to the UTS City Campus."
    )
]


# ---------------------------------------------------------
# Database Initialisation
# ---------------------------------------------------------

def create_database():

    # Make sure parent directory exists.
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # IMPORTANT:
    # Do NOT DROP the table.
    #
    # CREATE TABLE IF NOT EXISTS means existing CRUD data
    # survives container restarts.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campus_resources (
            resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            building TEXT NOT NULL,
            floor TEXT,
            capacity INTEGER,
            availability_status TEXT NOT NULL,
            opening_hours TEXT,
            location TEXT,
            description TEXT,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check whether database already contains data.
    cursor.execute("""
        SELECT COUNT(*)
        FROM campus_resources
    """)

    count = cursor.fetchone()[0]

    # Only seed the database when it is empty.
    if count == 0:

        cursor.executemany("""
            INSERT INTO campus_resources (
                resource_name,
                resource_type,
                building,
                floor,
                capacity,
                availability_status,
                opening_hours,
                location,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, RESOURCES)

        conn.commit()

        print(
            f"Database initialised with "
            f"{len(RESOURCES)} campus resources."
        )

    else:

        print(
            f"Existing database detected. "
            f"Keeping {count} campus resources."
        )

    conn.close()

    print(
        f"Database path: {DB_PATH}"
    )


if __name__ == "__main__":
    create_database()
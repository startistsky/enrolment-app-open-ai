import sqlite3
from pathlib import Path


# Store the database inside the student-3/database folder
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campus_resources.db"


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Recreate the table so the seed script can be run again safely
    cursor.execute("DROP TABLE IF EXISTS campus_resources")

    cursor.execute("""
        CREATE TABLE campus_resources (
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

    resources = [
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
    """, resources)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM campus_resources")
    count = cursor.fetchone()[0]

    conn.close()

    print(f"Database created successfully: {DB_PATH}")
    print(f"{count} campus resources inserted.")


if __name__ == "__main__":
    create_database()
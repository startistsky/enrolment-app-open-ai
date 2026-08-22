import sqlite3
import os


# Project root:
# student-5/
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# Database:
# student-5/database/career.db
DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE = os.path.join(
    DATABASE_DIR,
    "career.db"
)


def get_db():
    """
    Open SQLite database connection.
    """

    # Make sure database folder exists
    os.makedirs(
        DATABASE_DIR,
        exist_ok=True
    )

    db = sqlite3.connect(
        DATABASE
    )

    # Return rows as dictionary-like objects
    db.row_factory = sqlite3.Row

    # Enable foreign keys
    db.execute(
        "PRAGMA foreign_keys = ON"
    )

    return db


def init_db():

    db = get_db()

    db.executescript("""

        /* =========================
           JOBS
        ========================= */

        CREATE TABLE IF NOT EXISTS jobs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            company TEXT NOT NULL,

            location TEXT,

            industry TEXT,

            job_type TEXT,

            description TEXT,

            requirements TEXT,

            salary TEXT,

            application_url TEXT,

            created_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );


        /* =========================
           CAREER PREFERENCES
        ========================= */

        CREATE TABLE IF NOT EXISTS career_preferences (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            locations TEXT,

            industries TEXT,

            job_types TEXT,

            skills TEXT,

            career_goals TEXT,

            created_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            updated_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );


        /* =========================
           SAVED JOBS
        ========================= */

        CREATE TABLE IF NOT EXISTS saved_jobs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL UNIQUE,

            saved_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        );


        /* =========================
           APPLICATIONS
        ========================= */

        CREATE TABLE IF NOT EXISTS applications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL,

            status TEXT
                DEFAULT 'Interested',

            notes TEXT,

            applied_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        );


        /* =========================
           AI JOB ANALYSIS
        ========================= */

        CREATE TABLE IF NOT EXISTS job_ai_analysis (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL UNIQUE,

            skills TEXT,

            qualifications TEXT,

            experience TEXT,

            ats_keywords TEXT,

            summary TEXT,

            created_at
                TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        );

    """)

    db.commit()
    db.close()


if __name__ == "__main__":

    init_db()

    print(
        f"Database ready: {DATABASE}"
    )
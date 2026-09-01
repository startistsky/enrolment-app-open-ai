import os
import sqlite3
from pathlib import Path

# Databse config
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_DIR = BASE_DIR / "database"

DATABASE = DATABASE_DIR / "career.db"

# Database connection
def get_db():

    os.makedirs(
        DATABASE_DIR,
        exist_ok=True
    )

    db = sqlite3.connect(
        DATABASE,
        timeout=10,
        check_same_thread=False
    )

    db.row_factory = sqlite3.Row

    # Better behaviour for multiple Flask requests.
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA foreign_keys=ON")

    return db


# Helpers 

def column_exists(
    db,
    table,
    column
):

    columns = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(
        row["name"] == column
        for row in columns
    )


def add_column_if_missing(
    db,
    table,
    column,
    definition
):

    if not column_exists(
        db,
        table,
        column
    ):

        db.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


# Init table
# jobs, saved jobs, applications, ai job analysis

def init_db():

    db = get_db()

    try:

        db.execute(
            """
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
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_jobs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id INTEGER NOT NULL,

                saved_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(job_id),

                FOREIGN KEY(job_id)
                    REFERENCES jobs(id)
                    ON DELETE CASCADE
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id INTEGER NOT NULL,

                status TEXT DEFAULT 'Interested',

                notes TEXT,

                applied_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(job_id)
                    REFERENCES jobs(id)
                    ON DELETE CASCADE
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS job_ai_analysis (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id INTEGER UNIQUE NOT NULL,

                skills TEXT,

                qualifications TEXT,

                experience TEXT,

                ats_keywords TEXT,

                summary TEXT,

                FOREIGN KEY(job_id)
                    REFERENCES jobs(id)
                    ON DELETE CASCADE
            )
            """
        )

        # Application migration
        add_column_if_missing(
            db,
            "applications",
            "notes",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "applications",
            "applied_at",
            "TIMESTAMP"
        )


        # Job migration
        add_column_if_missing(
            db,
            "jobs",
            "salary",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "jobs",
            "application_url",
            "TEXT"
        )


        # Commit
        db.commit()

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# Database path 

if __name__ == "__main__":

    init_db()

    print(
        "Database ready:"
    )

    print(
        DATABASE
    )
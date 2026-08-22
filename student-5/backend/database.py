import os
import sqlite3

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE = os.path.join(
    DATABASE_DIR,
    "career.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

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


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# INITIALISE DATABASE
# ============================================================

def init_db():

    db = get_db()

    try:

        # ----------------------------------------------------
        # JOBS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # CAREER PROFILE
        # ----------------------------------------------------

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS career_profile (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT,

                email TEXT,

                education TEXT,

                skills TEXT,

                experience TEXT,

                interests TEXT,

                career_goals TEXT,

                preferred_locations TEXT,

                preferred_industries TEXT,

                preferred_job_types TEXT,

                updated_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # ----------------------------------------------------
        # SAVED JOBS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # APPLICATIONS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # AI JOB ANALYSIS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # AGENT RUNS
        # ----------------------------------------------------

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                agent_name TEXT,

                action TEXT,

                input_data TEXT,

                output_data TEXT,

                iteration INTEGER,

                created_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # ====================================================
        # DATABASE MIGRATIONS
        # ====================================================

        # This is the important part for your current error.
        #
        # Your existing career_profile table was created
        # before education was added.
        #
        # CREATE TABLE IF NOT EXISTS does NOT modify an
        # existing table.
        #
        # Therefore we explicitly add missing columns.

        add_column_if_missing(
            db,
            "career_profile",
            "name",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "email",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "education",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "skills",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "experience",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "interests",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "career_goals",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "preferred_locations",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "preferred_industries",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "preferred_job_types",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "career_profile",
            "updated_at",
            "TIMESTAMP"
        )


        # ----------------------------------------------------
        # APPLICATION MIGRATIONS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # JOB MIGRATIONS
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

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
import sys
from pathlib import Path
import pytest
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BACKEND_DIR = PROJECT_ROOT / "backend"
MODEL_DIR = BACKEND_DIR / "model"
CRUD_DIR = BACKEND_DIR / "crud"

# make path importable 
for path in (
    PROJECT_ROOT,
    BACKEND_DIR,
    MODEL_DIR,
    CRUD_DIR,
):
    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# import tools
from model.database import (
    get_db, 
    init_db
)

# Tests
def test_save_job():
    # Create database/tables
    init_db()

    db = get_db()

    try:
        # Create a test job
        db.execute(
            """
            INSERT INTO jobs (
                title,
                company,
                industry
            )
            VALUES (?, ?, ?)
            """,
            (
                "Python Developer",
                "Test Company",
                "Technology"
            )
        )

        db.commit()

        # Get the created job
        job = db.execute(
            """
            SELECT id
            FROM jobs
            WHERE title = ?
              AND company = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                "Python Developer",
                "Test Company"
            )
        ).fetchone()

        assert job is not None

        job_id = job["id"]

        # Remove any existing saved-job record
        db.execute(
            """
            DELETE FROM saved_jobs
            WHERE job_id = ?
            """,
            (job_id,)
        )

        db.commit()

        # Save the job
        db.execute(
            """
            INSERT INTO saved_jobs (job_id)
            VALUES (?)
            """,
            (job_id,)
        )

        db.commit()

        # Verify the job was saved
        saved_job = db.execute(
            """
            SELECT job_id
            FROM saved_jobs
            WHERE job_id = ?
            """,
            (job_id,)
        ).fetchone()

        assert saved_job is not None
        assert saved_job["job_id"] == job_id

    finally:
        # Clean up test data
        try:
            db.execute(
                "DELETE FROM saved_jobs WHERE job_id = ?",
                (job_id,)
            )

            db.execute(
                "DELETE FROM jobs WHERE id = ?",
                (job_id,)
            )

            db.commit()

        except (UnboundLocalError, NameError):
            db.rollback()

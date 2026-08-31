from model.database import get_db, init_db


def test_save_job():

    # Create database/tables
    init_db()

    db = get_db()

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

    # Get the created job ID
    job = db.execute(
        """
        SELECT id
        FROM jobs
        WHERE title = ?
        """,
        ("Python Developer",)
    ).fetchone()

    job_id = job["id"]

    # Save the job
    db.execute(
        """
        INSERT INTO saved_jobs (job_id)
        VALUES (?)
        """,
        (job_id,)
    )

    db.commit()

    # Check that the job was saved
    saved_job = db.execute(
        """
        SELECT *
        FROM saved_jobs
        WHERE job_id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    assert saved_job is not None
    assert saved_job["job_id"] == job_id
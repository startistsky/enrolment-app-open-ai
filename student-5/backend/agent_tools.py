from database import get_db

def get_job_tool(job_id):
    db = get_db()
    try:
        job = db.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = ?
            """,
            (job_id,)
        ).fetchone()

        if not job:
            return None

        return dict(job)

    finally:
        db.close()

def analyse_job_tool(job):
    from ai_service import analyse_job

    return analyse_job(
        job.get("description", ""),
        job.get("requirements", "")
    )


def get_job_requirements_tool(job):
    return {
        "requirements": job.get(
            "requirements",
            ""
        ),
        "description": job.get(
            "description",
            ""
        )
    }
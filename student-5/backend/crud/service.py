from flask import (
    Blueprint,
    request,
    jsonify
)

from model.database import get_db

# CRUD services and routes
service = Blueprint(
    "service",
    __name__
)

# Jobs service 
@service.route(
    "/jobs",
    methods=["GET"]
)
def get_jobs():

    search = request.args.get(
        "search",
        ""
    )

    location = request.args.get(
        "location",
        ""
    )

    industry = request.args.get(
        "industry",
        ""
    )

    job_type = request.args.get(
        "job_type",
        ""
    )

    db = get_db()

    query = """
        SELECT *
        FROM jobs
        WHERE 1 = 1
    """

    params = []

    if search:

        query += """
            AND (
                title LIKE ?
                OR company LIKE ?
                OR description LIKE ?
            )
        """

        term = f"%{search}%"

        params.extend([
            term,
            term,
            term
        ])

    if location:

        query += """
            AND location LIKE ?
        """

        params.append(
            f"%{location}%"
        )

    if industry:

        query += """
            AND industry LIKE ?
        """

        params.append( f"%{industry}%")

    if job_type:

        query += """
            AND job_type LIKE ?
        """

        params.append(
            f"%{job_type}%"
        )

    query += """
        ORDER BY created_at DESC
    """

    jobs = db.execute(
        query,
        params
    ).fetchall()

    db.close()

    return jsonify([
        dict(job)
        for job in jobs
    ])


# create job service
@service.route(
    "/jobs",
    methods=["POST"]
)
def create_job():

    data = request.json or {}

    if not data.get("title"):

        return jsonify({
            "error":
                "Job title is required"
        }), 400

    if not data.get("company"):

        return jsonify({
            "error":
                "Company is required"
        }), 400

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO jobs (
            title,
            company,
            location,
            industry,
            job_type,
            description,
            requirements,
            salary,
            application_url
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("title"),
            data.get("company"),
            data.get("location", ""),
            data.get("industry", ""),
            data.get("job_type", ""),
            data.get("description", ""),
            data.get("requirements", ""),
            data.get("salary", ""),
            data.get("application_url", "")
        )
    )

    db.commit()

    job_id = cursor.lastrowid

    db.close()

    return jsonify({
        "message":
            "Job created successfully",
        "job_id":
            job_id
    }), 201


# retrieve jobs service

@service.route(
    "/jobs/<int:job_id>",
    methods=["GET"]
)
def get_job(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    if not job:

        return jsonify({
            "error":
                "Job not found"
        }), 404

    return jsonify(
        dict(job)
    )


# update a job service
@service.route(
    "/jobs/<int:job_id>",
    methods=["PUT"]
)
def update_job(job_id):

    data = request.json or {}

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    if not existing:

        db.close()

        return jsonify({
            "error":
                "Job not found"
        }), 404

    db.execute(
        """
        UPDATE jobs

        SET
            title = ?,
            company = ?,
            location = ?,
            industry = ?,
            job_type = ?,
            description = ?,
            requirements = ?,
            salary = ?,
            application_url = ?

        WHERE id = ?
        """,
        (
            data.get("title", ""),
            data.get("company", ""),
            data.get("location", ""),
            data.get("industry", ""),
            data.get("job_type", ""),
            data.get("description", ""),
            data.get("requirements", ""),
            data.get("salary", ""),
            data.get("application_url", ""),
            job_id
        )
    )

    db.commit()

    db.close()

    return jsonify({
        "message":
            "Job updated successfully"
    })


# delete a job
@service.route(
    "/jobs/<int:job_id>",
    methods=["DELETE"]
)
def delete_job(job_id):

    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    if cursor.rowcount == 0:

        return jsonify({
            "error":
                "Job not found"
        }), 404

    return jsonify({
        "message":
            "Job deleted successfully"
    })


# retrieve saved jobs
@service.route(
    "/saved",
    methods=["GET"]
)
def get_saved_jobs():

    db = get_db()

    jobs = db.execute(
        """
        SELECT jobs.*

        FROM jobs

        JOIN saved_jobs
        ON jobs.id = saved_jobs.job_id

        ORDER BY saved_jobs.saved_at DESC
        """
    ).fetchall()

    db.close()

    return jsonify([
        dict(job)
        for job in jobs
    ])


# save a job sevice
@service.route(
    "/saved/<int:job_id>",
    methods=["POST"]
)
def save_job(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT id
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    if not job:

        db.close()

        return jsonify({
            "error":
                "Job not found"
        }), 404

    db.execute(
        """
        INSERT OR IGNORE INTO saved_jobs (
            job_id
        )

        VALUES (?)
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    return jsonify({
        "message":
            "Job saved successfully"
    })


# unsave a job service
@service.route(
    "/saved/<int:job_id>",
    methods=["DELETE"]
)
def delete_saved_job(job_id):

    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM saved_jobs
        WHERE job_id = ?
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    if cursor.rowcount == 0:

        return jsonify({
            "error":
                "Saved job not found"
        }), 404

    return jsonify({
        "message":
            "Saved job removed"
    })


# retrieve applications
@service.route(
    "/applications",
    methods=["GET"]
)
def get_applications():

    db = get_db()

    applications = db.execute(
        """
        SELECT
            applications.*,
            jobs.title,
            jobs.company

        FROM applications

        JOIN jobs
        ON applications.job_id = jobs.id

        ORDER BY applications.id DESC
        """
    ).fetchall()

    db.close()

    return jsonify([
        dict(application)
        for application in applications
    ])


# create applications 
@service.route(
    "/applications",
    methods=["POST"]
)
def create_application():

    data = request.json or {}

    job_id = data.get(
        "job_id"
    )

    if not job_id:

        return jsonify({
            "error":
                "job_id is required"
        }), 400

    db = get_db()

    job = db.execute(
        """
        SELECT id
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    if not job:

        db.close()

        return jsonify({
            "error":
                "Job not found"
        }), 404

    cursor = db.execute(
        """
        INSERT INTO applications (
            job_id,
            status,
            notes
        )

        VALUES (?, ?, ?)
        """,
        (
            job_id,
            data.get(
                "status",
                "Applied"
            ),
            data.get(
                "notes",
                ""
            )
        )
    )

    db.commit()

    application_id = cursor.lastrowid

    db.close()

    return jsonify({
        "message":
            "Application created",
        "application_id":
            application_id
    }), 201


# update an application
@service.route(
    "/applications/<int:application_id>",
    methods=["PUT"]
)
def update_application(application_id):

    data = request.json or {}

    db = get_db()

    cursor = db.execute(
        """
        UPDATE applications

        SET
            status = ?,
            notes = ?

        WHERE id = ?
        """,
        (
            data.get(
                "status",
                "Interested"
            ),
            data.get(
                "notes",
                ""
            ),
            application_id
        )
    )

    db.commit()

    db.close()

    if cursor.rowcount == 0:

        return jsonify({
            "error":
                "Application not found"
        }), 404

    return jsonify({
        "message":
            "Application updated"
    })


# delete an application
@service.route(
    "/applications/<int:application_id>",
    methods=["DELETE"]
)
def delete_application(application_id):

    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM applications
        WHERE id = ?
        """,
        (application_id,)
    )

    db.commit()

    db.close()

    if cursor.rowcount == 0:

        return jsonify({
            "error":
                "Application not found"
        }), 404

    return jsonify({
        "message":
            "Application deleted"
    })

# save a resume
@service.route(
    "/resume",
    methods=["POST"]
)
def save_resume():

    data = request.json or {}

    filename = data.get("filename")
    content = data.get("content")

    if not filename:
        return jsonify({
            "error": "Filename is required"
        }), 400

    if not content or not content.strip():
        return jsonify({
            "error": "Resume content is required"
        }), 400

    db = get_db()

    try:

        # Keep only one current resume.
        db.execute(
            """
            DELETE FROM resumes
            """
        )

        cursor = db.execute(
            """
            INSERT INTO resumes (
                filename,
                content
            )
            VALUES (?, ?)
            """,
            (
                filename,
                content
            )
        )

        db.commit()

        return jsonify({
            "message": "Resume saved successfully",
            "resume_id": cursor.lastrowid
        }), 201

    finally:
        db.close()


# get current resume
@service.route(
    "/resume",
    methods=["GET"]
)
def get_resume():

    db = get_db()

    try:

        resume = db.execute(
            """
            SELECT *
            FROM resumes
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not resume:

            return jsonify({
                "error": "No resume found"
            }), 404

        return jsonify(
            dict(resume)
        )

    finally:
        db.close()


# delete current resume
@service.route(
    "/resume",
    methods=["DELETE"]
)
def delete_resume():

    db = get_db()

    try:

        cursor = db.execute(
            """
            DELETE FROM resumes
            """
        )

        db.commit()

        if cursor.rowcount == 0:

            return jsonify({
                "error": "No resume found"
            }), 404

        return jsonify({
            "message": "Resume deleted successfully"
        })

    finally:
        db.close()


from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

from flask_cors import CORS

import os

from database import get_db, init_db
from ai_service import analyse_job, chat


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend"
)

TEMPLATES_DIR = os.path.join(
    FRONTEND_DIR,
    "templates"
)

STATIC_DIR = FRONTEND_DIR


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static"
)

CORS(app)


# ============================================================
# DATABASE
# ============================================================

init_db()


# ============================================================
# FRONTEND PAGES
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/index.html")
def index_html():
    return render_template("index.html")


@app.route("/job.html")
def job_page():
    return render_template("job.html")


@app.route("/dashboard.html")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/preferences.html")
def preferences_page():
    return render_template("preferences.html")


# ============================================================
# STATIC FILES
# ============================================================

@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "css"),
        filename
    )


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "js"),
        filename
    )


# ============================================================
# API STATUS
# ============================================================

@app.route("/api/status", methods=["GET"])
def status():

    return jsonify({
        "message": "CareerConnect API is running",
        "status": "success"
    })


# ============================================================
# JOBS
# ============================================================

# GET ALL JOBS
# Supports:
# ?search=
# ?location=
# ?industry=
# ?job_type=

@app.route("/jobs", methods=["GET"])
def get_jobs():

    search = request.args.get(
        "search",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    industry = request.args.get(
        "industry",
        ""
    ).strip()

    job_type = request.args.get(
        "job_type",
        ""
    ).strip()

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

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
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

        params.append(
            f"%{industry}%"
        )

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


# CREATE JOB

@app.route("/jobs", methods=["POST"])
def create_job():

    data = request.get_json(
        silent=True
    ) or {}

    if not data.get("title"):
        return jsonify({
            "error": "title is required"
        }), 400

    if not data.get("company"):
        return jsonify({
            "error": "company is required"
        }), 400

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO jobs
        (
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
            data.get("title", ""),
            data.get("company", ""),
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

    job = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Job created",
        "job": dict(job)
    }), 201


# GET SINGLE JOB

@app.route("/jobs/<int:job_id>", methods=["GET"])
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
            "error": "Job not found"
        }), 404

    return jsonify(
        dict(job)
    )


# UPDATE JOB

@app.route("/jobs/<int:job_id>", methods=["PUT"])
def update_job(job_id):

    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    existing = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    if not existing:

        db.close()

        return jsonify({
            "error": "Job not found"
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
            data.get(
                "title",
                existing["title"]
            ),
            data.get(
                "company",
                existing["company"]
            ),
            data.get(
                "location",
                existing["location"]
            ),
            data.get(
                "industry",
                existing["industry"]
            ),
            data.get(
                "job_type",
                existing["job_type"]
            ),
            data.get(
                "description",
                existing["description"]
            ),
            data.get(
                "requirements",
                existing["requirements"]
            ),
            data.get(
                "salary",
                existing["salary"]
            ),
            data.get(
                "application_url",
                existing["application_url"]
            ),
            job_id
        )
    )

    db.commit()

    updated = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Job updated",
        "job": dict(updated)
    })


# DELETE JOB

@app.route("/jobs/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):

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
            "error": "Job not found"
        }), 404

    # Remove related records first
    db.execute(
        """
        DELETE FROM saved_jobs
        WHERE job_id = ?
        """,
        (job_id,)
    )

    db.execute(
        """
        DELETE FROM applications
        WHERE job_id = ?
        """,
        (job_id,)
    )

    db.execute(
        """
        DELETE FROM job_ai_analysis
        WHERE job_id = ?
        """,
        (job_id,)
    )

    db.execute(
        """
        DELETE FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    return jsonify({
        "message": "Job deleted"
    })


# ============================================================
# SAVED JOBS
# ============================================================

# GET SAVED JOBS

@app.route("/saved", methods=["GET"])
def get_saved_jobs():

    db = get_db()

    jobs = db.execute(
        """
        SELECT
            jobs.*,
            saved_jobs.id AS saved_id,
            saved_jobs.saved_at
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


# SAVE JOB

@app.route(
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
            "error": "Job not found"
        }), 404

    db.execute(
        """
        INSERT OR IGNORE INTO saved_jobs
        (job_id)
        VALUES (?)
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    return jsonify({
        "message": "Job saved"
    })


# REMOVE SAVED JOB

@app.route(
    "/saved/<int:job_id>",
    methods=["DELETE"]
)
def remove_saved_job(job_id):

    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM saved_jobs
        WHERE job_id = ?
        """,
        (job_id,)
    )

    db.commit()

    deleted = cursor.rowcount

    db.close()

    if deleted == 0:

        return jsonify({
            "error": "Saved job not found"
        }), 404

    return jsonify({
        "message": "Job removed from saved jobs"
    })


# CHECK IF JOB IS SAVED

@app.route(
    "/saved/<int:job_id>",
    methods=["GET"]
)
def check_saved_job(job_id):

    db = get_db()

    saved = db.execute(
        """
        SELECT *
        FROM saved_jobs
        WHERE job_id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "saved": saved is not None
    })


# ============================================================
# CAREER PREFERENCES
# ============================================================

# GET PREFERENCES

@app.route(
    "/preferences",
    methods=["GET"]
)
def get_preferences():

    db = get_db()

    preferences = db.execute(
        """
        SELECT *
        FROM career_preferences
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    db.close()

    if not preferences:
        return jsonify({})

    return jsonify(
        dict(preferences)
    )


# CREATE / SAVE PREFERENCES

@app.route(
    "/preferences",
    methods=["POST"]
)
def save_preferences():

    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    # We only keep one current preference profile.
    db.execute(
        """
        DELETE FROM career_preferences
        """
    )

    cursor = db.execute(
        """
        INSERT INTO career_preferences
        (
            locations,
            industries,
            job_types,
            skills,
            career_goals
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.get(
                "locations",
                ""
            ),
            data.get(
                "industries",
                ""
            ),
            data.get(
                "job_types",
                ""
            ),
            data.get(
                "skills",
                ""
            ),
            data.get(
                "career_goals",
                ""
            )
        )
    )

    db.commit()

    preference_id = cursor.lastrowid

    preference = db.execute(
        """
        SELECT *
        FROM career_preferences
        WHERE id = ?
        """,
        (preference_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Preferences saved",
        "preferences": dict(preference)
    }), 201


# UPDATE PREFERENCES

@app.route(
    "/preferences/<int:preference_id>",
    methods=["PUT"]
)
def update_preferences(preference_id):

    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    existing = db.execute(
        """
        SELECT *
        FROM career_preferences
        WHERE id = ?
        """,
        (preference_id,)
    ).fetchone()

    if not existing:

        db.close()

        return jsonify({
            "error": "Preferences not found"
        }), 404

    db.execute(
        """
        UPDATE career_preferences
        SET
            locations = ?,
            industries = ?,
            job_types = ?,
            skills = ?,
            career_goals = ?
        WHERE id = ?
        """,
        (
            data.get(
                "locations",
                existing["locations"]
            ),
            data.get(
                "industries",
                existing["industries"]
            ),
            data.get(
                "job_types",
                existing["job_types"]
            ),
            data.get(
                "skills",
                existing["skills"]
            ),
            data.get(
                "career_goals",
                existing["career_goals"]
            ),
            preference_id
        )
    )

    db.commit()

    updated = db.execute(
        """
        SELECT *
        FROM career_preferences
        WHERE id = ?
        """,
        (preference_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Preferences updated",
        "preferences": dict(updated)
    })


# DELETE PREFERENCES

@app.route(
    "/preferences/<int:preference_id>",
    methods=["DELETE"]
)
def delete_preferences(preference_id):

    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM career_preferences
        WHERE id = ?
        """,
        (preference_id,)
    )

    db.commit()

    deleted = cursor.rowcount

    db.close()

    if deleted == 0:

        return jsonify({
            "error": "Preferences not found"
        }), 404

    return jsonify({
        "message": "Preferences deleted"
    })


# ============================================================
# APPLICATIONS
# ============================================================

# GET APPLICATIONS

@app.route(
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
            jobs.company,
            jobs.location
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


# CREATE APPLICATION

@app.route(
    "/applications",
    methods=["POST"]
)
def create_application():

    data = request.get_json(
        silent=True
    ) or {}

    job_id = data.get("job_id")

    if not job_id:

        return jsonify({
            "error": "job_id is required"
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
            "error": "Job not found"
        }), 404

    cursor = db.execute(
        """
        INSERT INTO applications
        (
            job_id,
            status,
            notes,
            applied_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
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

    application = db.execute(
        """
        SELECT
            applications.*,
            jobs.title,
            jobs.company
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id = ?
        """,
        (application_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Application added",
        "application": dict(application)
    }), 201


# GET ONE APPLICATION

@app.route(
    "/applications/<int:application_id>",
    methods=["GET"]
)
def get_application(application_id):

    db = get_db()

    application = db.execute(
        """
        SELECT
            applications.*,
            jobs.title,
            jobs.company,
            jobs.location
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id = ?
        """,
        (application_id,)
    ).fetchone()

    db.close()

    if not application:

        return jsonify({
            "error": "Application not found"
        }), 404

    return jsonify(
        dict(application)
    )


# UPDATE APPLICATION

@app.route(
    "/applications/<int:application_id>",
    methods=["PUT"]
)
def update_application(application_id):

    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    existing = db.execute(
        """
        SELECT *
        FROM applications
        WHERE id = ?
        """,
        (application_id,)
    ).fetchone()

    if not existing:

        db.close()

        return jsonify({
            "error": "Application not found"
        }), 404

    db.execute(
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
                existing["status"]
            ),
            data.get(
                "notes",
                existing["notes"] or ""
            ),
            application_id
        )
    )

    db.commit()

    updated = db.execute(
        """
        SELECT
            applications.*,
            jobs.title,
            jobs.company
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id = ?
        """,
        (application_id,)
    ).fetchone()

    db.close()

    return jsonify({
        "message": "Application updated",
        "application": dict(updated)
    })


# DELETE APPLICATION

@app.route(
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

    deleted = cursor.rowcount

    db.close()

    if deleted == 0:

        return jsonify({
            "error": "Application not found"
        }), 404

    return jsonify({
        "message": "Application deleted"
    })


# ============================================================
# AI JOB ANALYSIS
# ============================================================

@app.route(
    "/jobs/<int:job_id>/analyse",
    methods=["POST"]
)
def analyse(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    if not job:

        db.close()

        return jsonify({
            "error": "Job not found"
        }), 404

    result = analyse_job(
        job["description"] or "",
        job["requirements"] or ""
    )

    db.execute(
        """
        INSERT OR REPLACE INTO job_ai_analysis
        (
            job_id,
            skills,
            qualifications,
            experience,
            ats_keywords,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            result.get("skills", ""),
            result.get(
                "qualifications",
                ""
            ),
            result.get(
                "experience",
                ""
            ),
            result.get(
                "ats_keywords",
                ""
            ),
            result.get(
                "summary",
                ""
            )
        )
    )

    db.commit()

    db.close()

    return jsonify(result)


# GET STORED AI ANALYSIS

@app.route(
    "/jobs/<int:job_id>/analyse",
    methods=["GET"]
)
def get_analysis(job_id):

    db = get_db()

    analysis = db.execute(
        """
        SELECT *
        FROM job_ai_analysis
        WHERE job_id = ?
        """,
        (job_id,)
    ).fetchone()

    db.close()

    if not analysis:

        return jsonify({
            "error": "No analysis available"
        }), 404

    return jsonify(
        dict(analysis)
    )


# ============================================================
# AI CHAT
# ============================================================

@app.route(
    "/ai/chat",
    methods=["POST"]
)
def ai_chat():

    data = request.get_json(
        silent=True
    ) or {}

    message = data.get(
        "message",
        ""
    ).strip()

    if not message:

        return jsonify({
            "error": "Message is required"
        }), 400

    response = chat(message)

    return jsonify({
        "response": response
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error": "Resource not found"
    }), 404


@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "error": "Internal server error"
    }), 500


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5005,
        debug=True
    )
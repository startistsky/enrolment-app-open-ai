from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

from flask_cors import CORS

from database import get_db, init_db

from ai_service import (
    analyse_job,
    chat
)


app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend",
    static_url_path="/static"
)

CORS(app)

init_db()


# =========================================================
# FRONTEND
# =========================================================

@app.route("/")
def index():
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


@app.route("/admin.html")
def admin_page():
    return render_template("admin.html")


# =========================================================
# STATUS
# =========================================================

@app.route("/api/status")
def status():

    return jsonify({
        "message": "CareerConnect API is running",
        "status": "success"
    })


# =========================================================
# JOBS - GET
# =========================================================

@app.route("/jobs", methods=["GET"])
def get_jobs():

    search = request.args.get("search", "")
    location = request.args.get("location", "")
    industry = request.args.get("industry", "")
    job_type = request.args.get("job_type", "")

    db = get_db()

    query = """
        SELECT *
        FROM jobs
        WHERE title LIKE ?
    """

    params = [
        f"%{search}%"
    ]

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


# =========================================================
# JOBS - GET SINGLE
# =========================================================

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

    return jsonify(dict(job))


# =========================================================
# JOBS - CREATE
# =========================================================

@app.route("/jobs", methods=["POST"])
def create_job():

    data = request.get_json(silent=True) or {}

    if not data.get("title"):
        return jsonify({
            "error": "Job title is required."
        }), 400

    if not data.get("company"):
        return jsonify({
            "error": "Company is required."
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
        "message": "Job created successfully.",
        "job_id": job_id
    }), 201


# =========================================================
# JOBS - UPDATE
# =========================================================

@app.route("/jobs/<int:job_id>", methods=["PUT"])
def update_job(job_id):

    data = request.get_json(silent=True) or {}

    db = get_db()

    existing = db.execute(
        "SELECT id FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()

    if not existing:

        db.close()

        return jsonify({
            "error": "Job not found."
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
        "message": "Job updated successfully."
    })


# =========================================================
# JOBS - DELETE
# =========================================================

@app.route("/jobs/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):

    db = get_db()

    cursor = db.execute(
        "DELETE FROM jobs WHERE id = ?",
        (job_id,)
    )

    db.commit()

    deleted = cursor.rowcount

    db.close()

    if deleted == 0:

        return jsonify({
            "error": "Job not found."
        }), 404

    return jsonify({
        "message": "Job deleted successfully."
    })


# =========================================================
# SAVED JOBS - GET
# =========================================================

@app.route("/saved", methods=["GET"])
def get_saved_jobs():

    db = get_db()

    jobs = db.execute(
        """
        SELECT jobs.*
        FROM jobs
        INNER JOIN saved_jobs
            ON jobs.id = saved_jobs.job_id
        ORDER BY saved_jobs.saved_at DESC
        """
    ).fetchall()

    db.close()

    return jsonify([
        dict(job)
        for job in jobs
    ])


# =========================================================
# SAVED JOB - CREATE
# =========================================================

@app.route("/saved/<int:job_id>", methods=["POST"])
def save_job(job_id):

    db = get_db()

    job = db.execute(
        "SELECT id FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()

    if not job:

        db.close()

        return jsonify({
            "error": "Job not found."
        }), 404

    db.execute(
        """
        INSERT OR IGNORE INTO saved_jobs(job_id)
        VALUES (?)
        """,
        (job_id,)
    )

    db.commit()

    db.close()

    return jsonify({
        "message": "Job saved successfully."
    })


# =========================================================
# SAVED JOB - DELETE
# =========================================================

@app.route("/saved/<int:job_id>", methods=["DELETE"])
def unsave_job(job_id):

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
            "error": "Saved job not found."
        }), 404

    return jsonify({
        "message": "Job removed from saved jobs."
    })


# =========================================================
# PREFERENCES - GET
# =========================================================

@app.route("/preferences", methods=["GET"])
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

    return jsonify(dict(preferences))


# =========================================================
# PREFERENCES - CREATE/UPDATE
# =========================================================

@app.route("/preferences", methods=["POST"])
def save_preferences():

    data = request.get_json(silent=True) or {}

    db = get_db()

    db.execute(
        "DELETE FROM career_preferences"
    )

    db.execute(
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
            data.get("locations", ""),
            data.get("industries", ""),
            data.get("job_types", ""),
            data.get("skills", ""),
            data.get("career_goals", "")
        )
    )

    db.commit()

    db.close()

    return jsonify({
        "message": "Preferences saved successfully."
    })


# =========================================================
# PREFERENCES - DELETE
# =========================================================

@app.route("/preferences", methods=["DELETE"])
def delete_preferences():

    db = get_db()

    db.execute(
        "DELETE FROM career_preferences"
    )

    db.commit()

    db.close()

    return jsonify({
        "message": "Preferences cleared."
    })


# =========================================================
# RECOMMENDATIONS
# =========================================================

@app.route("/recommendations", methods=["GET"])
def recommendations():

    db = get_db()

    preferences = db.execute(
        """
        SELECT *
        FROM career_preferences
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    jobs = db.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY created_at DESC
        """
    ).fetchall()

    db.close()

    if not preferences:

        return jsonify([])

    preferences = dict(preferences)

    locations = (
        preferences.get("locations") or ""
    ).lower()

    industries = (
        preferences.get("industries") or ""
    ).lower()

    job_types = (
        preferences.get("job_types") or ""
    ).lower()

    skills = (
        preferences.get("skills") or ""
    ).lower()

    recommendations = []

    for job in jobs:

        job_dict = dict(job)

        score = 0

        location = (
            job_dict.get("location") or ""
        ).lower()

        industry = (
            job_dict.get("industry") or ""
        ).lower()

        job_type = (
            job_dict.get("job_type") or ""
        ).lower()

        text = (
            f"{job_dict.get('title', '')} "
            f"{job_dict.get('description', '')} "
            f"{job_dict.get('requirements', '')}"
        ).lower()

        if locations:

            for location_preference in locations.split(","):

                if location_preference.strip() in location:

                    score += 3

        if industries:

            for industry_preference in industries.split(","):

                if industry_preference.strip() in industry:

                    score += 3

        if job_types:

            for type_preference in job_types.split(","):

                if type_preference.strip() in job_type:

                    score += 3

        if skills:

            for skill in skills.split(","):

                skill = skill.strip()

                if skill and skill in text:

                    score += 2

        if score > 0:

            job_dict["match_score"] = score

            recommendations.append(job_dict)

    recommendations.sort(
        key=lambda job: job["match_score"],
        reverse=True
    )

    return jsonify(recommendations)


# =========================================================
# APPLICATIONS - GET
# =========================================================

@app.route("/applications", methods=["GET"])
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
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        ORDER BY applications.id DESC
        """
    ).fetchall()

    db.close()

    return jsonify([
        dict(application)
        for application in applications
    ])


# =========================================================
# APPLICATIONS - CREATE
# =========================================================

@app.route("/applications", methods=["POST"])
def create_application():

    data = request.get_json(silent=True) or {}

    job_id = data.get("job_id")

    if not job_id:

        return jsonify({
            "error": "job_id is required."
        }), 400

    db = get_db()

    job = db.execute(
        "SELECT id FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()

    if not job:

        db.close()

        return jsonify({
            "error": "Job not found."
        }), 404

    cursor = db.execute(
        """
        INSERT INTO applications
        (
            job_id,
            status,
            notes
        )
        VALUES (?, ?, ?)
        """,
        (
            job_id,
            data.get("status", "Applied"),
            data.get("notes", "")
        )
    )

    db.commit()

    application_id = cursor.lastrowid

    db.close()

    return jsonify({
        "message": "Application created.",
        "application_id": application_id
    }), 201


# =========================================================
# APPLICATIONS - UPDATE
# =========================================================

@app.route(
    "/applications/<int:application_id>",
    methods=["PUT"]
)
def update_application(application_id):

    data = request.get_json(silent=True) or {}

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
            data.get("status", "Applied"),
            data.get("notes", ""),
            application_id
        )
    )

    db.commit()

    updated = cursor.rowcount

    db.close()

    if updated == 0:

        return jsonify({
            "error": "Application not found."
        }), 404

    return jsonify({
        "message": "Application updated."
    })


# =========================================================
# APPLICATIONS - DELETE
# =========================================================

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
            "error": "Application not found."
        }), 404

    return jsonify({
        "message": "Application deleted."
    })


# =========================================================
# AI ANALYSIS
# =========================================================

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
            "error": "Job not found."
        }), 404

    result = analyse_job(
        job["description"],
        job["requirements"]
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
            result["skills"],
            result["qualifications"],
            result["experience"],
            result["ats_keywords"],
            result["summary"]
        )
    )

    db.commit()

    db.close()

    return jsonify(result)


# =========================================================
# AI CHAT
# =========================================================

@app.route("/ai/chat", methods=["POST"])
def ai_chat():

    data = request.get_json(silent=True) or {}

    message = data.get("message", "")

    if not message:

        return jsonify({
            "error": "Message is required."
        }), 400

    response = chat(message)

    return jsonify({
        "response": response
    })


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5005,
        debug=True
    )
import os

from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

from flask_cors import CORS

from database import (
    get_db,
    init_db
)

from ai_service import (
    analyse_job,
    career_chat,
    check_ollama
)

from agent import (
    run_career_agent
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

    return render_template(
        "index.html"
    )


@app.route("/job.html")
def job_page():

    return render_template(
        "job.html"
    )


@app.route("/dashboard.html")
def dashboard_page():

    return render_template(
        "dashboard.html"
    )


@app.route("/admin.html")
def admin_page():

    return render_template(
        "admin.html"
    )


# =========================================================
# STATUS
# =========================================================

@app.route("/api/ai/status")
def ai_status():

    return jsonify(
        check_ollama()
    )

# =========================================================
# JOBS - READ
# =========================================================

@app.route(
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
# JOBS - CREATE
# =========================================================

@app.route(
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


# =========================================================
# JOB - READ
# =========================================================

@app.route(
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


# =========================================================
# JOB - UPDATE
# =========================================================

@app.route(
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


# =========================================================
# JOB - DELETE
# =========================================================

@app.route(
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


# =========================================================
# SAVED JOBS
# =========================================================

@app.route(
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
            "error":
                "Job not found"
        }), 404


    db.execute(

        """
        INSERT OR IGNORE
        INTO saved_jobs(job_id)

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


@app.route(
    "/saved/<int:job_id>",
    methods=["DELETE"]
)
def delete_saved_job(job_id):

    db = get_db()


    db.execute(

        """
        DELETE FROM saved_jobs
        WHERE job_id = ?
        """,

        (job_id,)
    )


    db.commit()

    db.close()


    return jsonify({
        "message":
            "Saved job removed"
    })


# =========================================================
# CAREER PROFILE
# =========================================================

@app.route(
    "/profile",
    methods=["GET"]
)
def get_profile():

    db = get_db()


    profile = db.execute(

        """
        SELECT *
        FROM career_profile
        WHERE id = 1
        """
    ).fetchone()


    db.close()


    if not profile:

        return jsonify({})


    return jsonify(
        dict(profile)
    )


@app.route(
    "/profile",
    methods=["POST"]
)
def save_profile():

    data = request.json or {}

    db = get_db()


    db.execute(
        "DELETE FROM career_profile"
    )


    db.execute(

        """
        INSERT INTO career_profile (

            id,
            locations,
            industries,
            job_types,
            skills,
            career_goals,
            education,
            experience

        )

        VALUES (
            1, ?, ?, ?, ?, ?, ?, ?
        )
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
            ),

            data.get(
                "education",
                ""
            ),

            data.get(
                "experience",
                ""
            )
        )
    )


    db.commit()

    db.close()


    return jsonify({
        "message":
            "Career profile saved"
    })


# =========================================================
# CAREER AGENT
# =========================================================

@app.route(
    "/agent/match",
    methods=["POST"]
)
def agent_match():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        db = get_db()

        profile = db.execute(
            """
            SELECT *
            FROM career_profile
            LIMIT 1
            """
        ).fetchone()

        jobs = db.execute(
            """
            SELECT *
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()

        db.close()

        if not profile:

            return jsonify({
                "success": False,
                "error": "Please create your career profile first."
            }), 400

        profile = dict(profile)

        jobs = [
            dict(job)
            for job in jobs
        ]

        result = run_career_agent(
            profile,
            jobs
        )

        return jsonify(result)

    except Exception as error:

        print(
            "CAREER AGENT ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

# =========================================================
# AI JOB / ATS ANALYSIS
# =========================================================
@app.route(
    "/jobs/<int:job_id>/analyse",
    methods=["POST"]
)
def analyse(job_id):

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

            return jsonify({
                "success": False,
                "error": "Job not found"
            }), 404

        result = analyse_job(
            job["description"] or "",
            job["requirements"] or ""
        )

        # -------------------------------------------------
        # Convert values into SQLite-safe strings
        # -------------------------------------------------

        def sqlite_text(value):

            if value is None:
                return ""

            if isinstance(value, list):
                return ", ".join(
                    str(item)
                    for item in value
                )

            if isinstance(value, dict):
                return json.dumps(
                    value,
                    ensure_ascii=False
                )

            return str(value)

        skills = sqlite_text(
            result.get("skills")
        )

        qualifications = sqlite_text(
            result.get("qualifications")
        )

        experience = sqlite_text(
            result.get("experience")
        )

        ats_keywords = sqlite_text(
            result.get("ats_keywords")
        )

        summary = sqlite_text(
            result.get("summary")
        )

        # -------------------------------------------------
        # Save analysis
        # -------------------------------------------------

        db.execute(
            """
            INSERT OR REPLACE INTO job_ai_analysis (
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
                skills,
                qualifications,
                experience,
                ats_keywords,
                summary
            )
        )

        db.commit()

        # -------------------------------------------------
        # Return clean frontend JSON
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "skills": result.get("skills", []),
            "qualifications": result.get(
                "qualifications",
                []
            ),
            "experience": result.get(
                "experience",
                []
            ),
            "ats_keywords": result.get(
                "ats_keywords",
                []
            ),
            "summary": summary
        })

    except Exception as error:

        db.rollback()

        print(
            "JOB ANALYSIS ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    finally:

        db.close()

# =========================================================
# APPLICATIONS
# =========================================================

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


@app.route(
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


@app.route(
    "/applications/<int:application_id>",
    methods=["PUT"]
)
def update_application(
    application_id
):

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


@app.route(
    "/applications/<int:application_id>",
    methods=["DELETE"]
)
def delete_application(
    application_id
):

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


# =========================================================
# AI CHAT
# =========================================================

@app.route(
    "/ai/chat",
    methods=["POST"]
)
def ai_chat():

    data = request.json or {}

    message = data.get(
        "message",
        ""
    )


    if not message:

        return jsonify({
            "error":
                "Message is required"
        }), 400


    job_id = data.get(
        "job_id"
    )


    job = None


    if job_id:

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


    response = career_chat(

        message,

        dict(job)
        if job
        else None

    )
    
    return jsonify({
        "response":
            response
    })


# run 
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5005,
        debug=True
    )
from flask import Flask, request, jsonify
from flask_cors import CORS

from database import get_db, init_db
from ai_service import analyse_job, chat


app = Flask(__name__)

CORS(app)

init_db()


# JOBS
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

    params = [f"%{search}%"]


    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")


    if industry:
        query += " AND industry LIKE ?"
        params.append(f"%{industry}%")


    if job_type:
        query += " AND job_type LIKE ?"
        params.append(f"%{job_type}%")


    query += " ORDER BY created_at DESC"


    jobs = db.execute(
        query,
        params
    ).fetchall()

    db.close()

    return jsonify([
        dict(job)
        for job in jobs
    ])


@app.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):

    db = get_db()

    job = db.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()

    db.close()

    if not job:
        return jsonify({
            "error": "Job not found"
        }), 404

    return jsonify(dict(job))


# SAVE JOB
@app.route("/saved/<int:job_id>", methods=["POST"])
def save_job(job_id):

    db = get_db()

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
        "message": "Job saved"
    })


@app.route("/saved", methods=["GET"])
def get_saved_jobs():

    db = get_db()

    jobs = db.execute("""
        SELECT jobs.*
        FROM jobs
        JOIN saved_jobs
            ON jobs.id = saved_jobs.job_id
        ORDER BY saved_jobs.saved_at DESC
    """).fetchall()

    db.close()

    return jsonify([
        dict(job)
        for job in jobs
    ])


# CAREER PREFERENCES
@app.route("/preferences", methods=["GET"])
def get_preferences():

    db = get_db()

    preferences = db.execute(
        """
        SELECT *
        FROM career_preferences
        LIMIT 1
        """
    ).fetchone()

    db.close()

    if not preferences:
        return jsonify({})

    return jsonify(dict(preferences))


@app.route("/preferences", methods=["POST"])
def save_preferences():

    data = request.json

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
            data.get("locations"),
            data.get("industries"),
            data.get("job_types"),
            data.get("skills"),
            data.get("career_goals")
        )
    )

    db.commit()
    db.close()

    return jsonify({
        "message": "Preferences saved"
    })


# APPLICATIONS
@app.route("/applications", methods=["GET"])
def get_applications():

    db = get_db()

    applications = db.execute("""
        SELECT
            applications.*,
            jobs.title,
            jobs.company
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        ORDER BY applications.id DESC
    """).fetchall()

    db.close()

    return jsonify([
        dict(application)
        for application in applications
    ])


@app.route("/applications", methods=["POST"])
def create_application():

    data = request.json

    db = get_db()

    db.execute(
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
            data["job_id"],
            data.get("status", "Interested"),
            data.get("notes", "")
        )
    )

    db.commit()
    db.close()

    return jsonify({
        "message": "Application added"
    })


@app.route(
    "/applications/<int:application_id>",
    methods=["PUT"]
)
def update_application(application_id):

    data = request.json

    db = get_db()

    db.execute(
        """
        UPDATE applications
        SET status = ?, notes = ?
        WHERE id = ?
        """,
        (
            data["status"],
            data.get("notes", ""),
            application_id
        )
    )

    db.commit()
    db.close()

    return jsonify({
        "message": "Application updated"
    })



# AI JOB ANALYSIS
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
        return jsonify({
            "error": "Job not found"
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


# AI CHAT

@app.route("/ai/chat", methods=["POST"])
def ai_chat():

    data = request.json

    response = chat(
        data.get("message", "")
    )

    return jsonify({
        "response": response
    })


if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
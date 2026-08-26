from flask import Blueprint, request, jsonify

from database import get_db

from ai_service import (
    analyse_job,
    check_ollama
)

from agent import (
    run_career_agent
)

ai_routes = Blueprint(
    "ai_routes",
    __name__
)


# AI status
@ai_routes.route(
    "/ai/status",
    methods=["GET"]
)
def ai_status():

    try:

        return jsonify(
            check_ollama()
        )

    except Exception as error:

        print(
            "AI STATUS ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "available": False,
            "error": str(error)
        }), 500


# AI job analyse 
@ai_routes.route(
    "/jobs/<int:job_id>/analyse",
    methods=["POST"]
)
def analyse_job_route(job_id):

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
                "error": "Job not found."
            }), 404

        # run analysis
        result = analyse_job(
            job["description"] or "",
            job["requirements"] or ""
        )

        # Convert AI results to database-safe strings
        skills = ", ".join(
            str(item)
            for item in result.get(
                "skills",
                []
            )
        )

        qualifications = ", ".join(
            str(item)
            for item in result.get(
                "qualifications",
                []
            )
        )

        experience = ", ".join(
            str(item)
            for item in result.get(
                "experience",
                []
            )
        )

        ats_keywords = ", ".join(
            str(item)
            for item in result.get(
                "ats_keywords",
                []
            )
        )

        summary = str(
            result.get(
                "summary",
                ""
            )
        )

        # Save analysis
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

        return jsonify({
            "success": True,
            "job_id": job_id,

            "skills": result.get(
                "skills",
                []
            ),

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
        }), 200

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


# Get saved ai job analysis 
@ai_routes.route(
    "/jobs/<int:job_id>/analysis",
    methods=["GET"]
)
def get_job_analysis(job_id):

    db = get_db()

    try:

        analysis = db.execute(
            """
            SELECT *
            FROM job_ai_analysis
            WHERE job_id = ?
            """,
            (job_id,)
        ).fetchone()

        if not analysis:

            return jsonify({
                "success": False,
                "error": "No AI analysis found for this job."
            }), 404

        return jsonify({
            "success": True,
            "analysis": dict(analysis)
        }), 200

    except Exception as error:

        print(
            "GET AI ANALYSIS ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    finally:

        db.close()


# Career agent for a job
@ai_routes.route(
    "/jobs/<int:job_id>/agent",
    methods=["POST"]
)
def job_agent(job_id):

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not message:

        return jsonify({
            "success": False,
            "error": "Message is required."
        }), 400

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
                "error": "Job not found."
            }), 404

        # Run agent
        result = run_career_agent(
            dict(job),
            message
        )

        if not result.get("success"):

            return jsonify(
                result
            ), 500

        return jsonify(
            result
        ), 200

    except Exception as error:

        print(
            "CAREER AGENT ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    finally:

        db.close()


# AI chat
@ai_routes.route(
    "/ai/chat",
    methods=["POST"]
)
def ai_chat():

    db = get_db()

    try:
        # Read JSON request
        data = request.get_json(
            silent=True
        ) or {}

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        job_id = data.get(
            "job_id"
        )

        if not message:

            return jsonify({
                "success": False,
                "error": "Message is required."
            }), 400

        if job_id is None:

            return jsonify({
                "success": False,
                "error": "Job ID is required."
            }), 400

        try:

            job_id = int(job_id)

        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "success": False,
                "error": "Invalid job ID."
            }), 400
        
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
                "error": "Job not found."
            }), 404

        # run agent
        result = run_career_agent(
            dict(job),
            message
        )

        # handle error
        if not result.get("success"):

            return jsonify(
                result
            ), 500

        return jsonify(
            result
        ), 200

    except Exception as error:

        print(
            "AI CHAT ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    finally:

        db.close()
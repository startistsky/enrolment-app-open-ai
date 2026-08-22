from database import get_db


# =========================================
# Career & Internship Agent
# =========================================

def run_career_agent(profile):

    """
    Career & Internship Agent

    Reads a student's career profile,
    retrieves available opportunities,
    matches the profile against jobs,
    ranks opportunities,
    identifies skill gaps,
    and explains recommendations.
    """

    locations = profile.get(
        "locations",
        ""
    )

    industries = profile.get(
        "industries",
        ""
    )

    job_types = profile.get(
        "job_types",
        ""
    )

    skills = profile.get(
        "skills",
        ""
    )

    career_goals = profile.get(
        "career_goals",
        ""
    )


    # =====================================
    # Convert preferences into lists
    # =====================================

    preferred_locations = split_values(
        locations
    )

    preferred_industries = split_values(
        industries
    )

    preferred_job_types = split_values(
        job_types
    )

    user_skills = split_values(
        skills
    )


    # =====================================
    # Get jobs
    # =====================================

    db = get_db()

    jobs = db.execute("""
        SELECT *
        FROM jobs
        ORDER BY created_at DESC
    """).fetchall()

    db.close()


    recommendations = []


    # =====================================
    # Analyse every job
    # =====================================

    for job in jobs:

        result = analyse_match(
            job,
            preferred_locations,
            preferred_industries,
            preferred_job_types,
            user_skills,
            career_goals
        )

        recommendations.append(
            result
        )


    # =====================================
    # Rank jobs
    # =====================================

    recommendations.sort(
        key=lambda item:
        item["match_score"],
        reverse=True
    )


    # Only return the top 10
    recommendations = recommendations[:10]


    return {

        "agent": "Career & Internship Agent",

        "profile": {

            "locations": locations,

            "industries": industries,

            "job_types": job_types,

            "skills": skills,

            "career_goals": career_goals

        },

        "recommendations":
            recommendations

    }


# =========================================
# Analyse one job
# =========================================

def analyse_match(
    job,
    locations,
    industries,
    job_types,
    skills,
    career_goals
):

    score = 0

    reasons = []

    matched_skills = []

    skill_gaps = []


    # -------------------------------------
    # Build searchable job text
    # -------------------------------------

    job_text = " ".join([

        job["title"] or "",

        job["company"] or "",

        job["location"] or "",

        job["industry"] or "",

        job["job_type"] or "",

        job["description"] or "",

        job["requirements"] or ""

    ]).lower()


    # =====================================
    # Location
    # =====================================

    for location in locations:

        if location in job_text:

            score += 20

            reasons.append(
                f"Matches your preferred location: "
                f"{location.title()}"
            )

            break


    # =====================================
    # Industry
    # =====================================

    for industry in industries:

        if industry in job_text:

            score += 20

            reasons.append(
                f"Matches your preferred industry: "
                f"{industry.title()}"
            )

            break


    # =====================================
    # Job type
    # =====================================

    for job_type in job_types:

        if job_type in job_text:

            score += 15

            reasons.append(
                f"Matches your preferred opportunity type: "
                f"{job_type.title()}"
            )

            break


    # =====================================
    # Skills
    # =====================================

    for skill in skills:

        if skill in job_text:

            score += 8

            matched_skills.append(
                skill.title()
            )

        else:

            skill_gaps.append(
                skill.title()
            )


    if matched_skills:

        reasons.append(
            "Your skills match some of the "
            "requirements for this opportunity."
        )


    # =====================================
    # Career goals
    # =====================================

    if career_goals:

        goal_words = [

            word.lower().strip(
                ".,!?;:"
            )

            for word in career_goals.split()

            if len(
                word.strip(".,!?;:")
            ) >= 5

        ]


        goal_matches = [

            word

            for word in goal_words

            if word in job_text

        ]


        if goal_matches:

            score += 15

            reasons.append(
                "This opportunity aligns "
                "with your career goals."
            )


    # =====================================
    # Maximum score
    # =====================================

    score = min(
        score,
        100
    )


    # =====================================
    # Default explanation
    # =====================================

    if not reasons:

        reasons.append(
            "This opportunity may be worth "
            "exploring based on the available "
            "job information."
        )


    return {

        "job": dict(job),

        "match_score": score,

        "reasons": reasons,

        "matched_skills":
            matched_skills,

        "skill_gaps":
            skill_gaps

    }


# =========================================
# Utility
# =========================================

def split_values(value):

    if not value:

        return []


    return [

        item.strip().lower()

        for item in value.split(",")

        if item.strip()

    ]
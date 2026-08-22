# =========================================
# AI Service
# =========================================

def analyse_job(
    description,
    requirements
):

    text = (
        f"{description or ''} "
        f"{requirements or ''}"
    )


    return {

        "skills":
            "Review the job requirements "
            "for technical and professional skills.",

        "qualifications":
            "Review the listed education "
            "and qualification requirements.",

        "experience":
            "Review the experience requirements "
            "listed by the employer.",

        "ats_keywords":
            text[:300],

        "summary":
            (
                description
                or
                "No job description available."
            )

    }


def chat(message):

    if not message:

        return (
            "Ask me something about this "
            "career opportunity."
        )


    message_lower = message.lower()


    if "skill" in message_lower:

        return (
            "Review the job requirements and "
            "compare them with your current skills. "
            "The Career & Internship Agent can also "
            "identify potential skill gaps."
        )


    if "apply" in message_lower:

        return (
            "Before applying, review the job "
            "requirements, tailor your resume "
            "to the role, and highlight relevant "
            "projects and experience."
        )


    if "salary" in message_lower:

        return (
            "Check the salary information listed "
            "on the opportunity. If it is not "
            "provided, consider contacting the "
            "employer."
        )


    return (
        "I can help you understand the job, "
        "identify relevant skills, prepare "
        "for an application, and explore "
        "career opportunities."
    )
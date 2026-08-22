import re


def extract_skills(text):

    text = text.lower()

    known_skills = [
        "python",
        "javascript",
        "typescript",
        "java",
        "c++",
        "c#",
        "sql",
        "html",
        "css",
        "react",
        "node.js",
        "flask",
        "django",
        "git",
        "github",
        "aws",
        "azure",
        "docker",
        "machine learning",
        "data analysis",
        "excel",
        "communication",
        "leadership",
        "project management",
        "marketing",
        "sales"
    ]

    found = []

    for skill in known_skills:

        if skill in text:
            found.append(skill)

    return found


def analyse_job(
    description,
    requirements
):

    combined = (
        description +
        " " +
        requirements
    )


    skills = extract_skills(
        combined
    )


    if not skills:

        skills = [
            "Communication",
            "Problem solving",
            "Teamwork"
        ]


    qualification_matches = re.findall(
        r"(?:degree|bachelor|master|diploma|certificate)[^.,;\n]*",
        combined,
        flags=re.IGNORECASE
    )


    experience_matches = re.findall(
        r"(?:\d+\+?\s+years?)[^.,;\n]*",
        combined,
        flags=re.IGNORECASE
    )


    ats_keywords = list(
        dict.fromkeys(
            skills +
            [
                "teamwork",
                "communication",
                "problem solving"
            ]
        )
    )


    summary = (
        "This role appears to focus on "
        "the skills and requirements listed "
        "in the job description. "
        "Review the required skills and "
        "highlight matching experience "
        "on your resume."
    )


    return {

        "skills":
            ", ".join(skills),

        "qualifications":
            ", ".join(
                qualification_matches
            ) or "Review the job requirements.",

        "experience":
            ", ".join(
                experience_matches
            ) or "Experience requirements should be reviewed.",

        "ats_keywords":
            ", ".join(
                ats_keywords
            ),

        "summary":
            summary
    }


def chat(message):

    message_lower = message.lower()


    if "resume" in message_lower:

        return (
            "For this job, tailor your resume "
            "to the required skills and use "
            "specific examples of your experience."
        )


    if "interview" in message_lower:

        return (
            "Prepare examples using the STAR "
            "method: Situation, Task, Action "
            "and Result."
        )


    if "skill" in message_lower:

        return (
            "Focus on the skills listed in the "
            "job requirements and identify "
            "which ones you already have."
        )


    if "apply" in message_lower:

        return (
            "Before applying, check the job "
            "requirements, tailor your resume, "
            "and prepare a short cover letter."
        )


    return (
        "I can help you understand the job, "
        "identify important skills, prepare "
        "for an interview, improve your resume, "
        "or decide whether the opportunity "
        "matches your goals."
    )
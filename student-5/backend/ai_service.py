def analyse_job(description, requirements):

    description = description or ""
    requirements = requirements or ""

    text = f"{description} {requirements}".lower()

    skills = []

    possible_skills = [
        "python",
        "javascript",
        "html",
        "css",
        "react",
        "sql",
        "java",
        "c++",
        "flask",
        "django",
        "git",
        "github",
        "excel",
        "communication",
        "leadership",
        "marketing",
        "data analysis",
        "machine learning",
        "figma"
    ]

    for skill in possible_skills:

        if skill in text:
            skills.append(skill.title())

    if not skills:
        skills.append(
            "Review the job description for specific technical and transferable skills."
        )

    qualifications = (
        "Review the employer requirements for degree, "
        "certification and educational expectations."
    )

    experience = (
        "Review the job description for required years of experience. "
        "Students should highlight relevant projects, coursework, "
        "internships and extracurricular experience."
    )

    ats_keywords = ", ".join(skills)

    summary = (
        "This role should be assessed against your preferred "
        "industry, location, job type and skills. "
        "Focus your application on the requirements that match "
        "your strongest experience."
    )

    return {
        "skills": ", ".join(skills),
        "qualifications": qualifications,
        "experience": experience,
        "ats_keywords": ats_keywords,
        "summary": summary
    }


def chat(message):

    message = (message or "").strip()

    if not message:
        return "Please enter a question."

    message_lower = message.lower()

    if "resume" in message_lower or "cv" in message_lower:

        return (
            "For this job, tailor your CV to the required skills. "
            "Put your strongest matching skills near the top and "
            "include measurable project or work outcomes."
        )

    if "interview" in message_lower:

        return (
            "Prepare examples using the STAR method: Situation, "
            "Task, Action and Result. Focus on examples that "
            "demonstrate the skills requested in the job description."
        )

    if "skill" in message_lower:

        return (
            "Compare your current skills with the job requirements. "
            "Prioritise the skills that appear repeatedly in the "
            "description and requirements."
        )

    return (
        "I can help you understand this opportunity, improve your "
        "CV, prepare for an interview, identify useful skills and "
        "decide whether the role matches your career goals."
    )
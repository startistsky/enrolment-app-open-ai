
from model.database import get_db, init_db

jobs = [
    {
        "title": "Graduate Software Engineer",
        "company": "TechNova",
        "location": "Sydney",
        "industry": "Technology",
        "job_type": "Graduate",

        "description": """
Join our software engineering team to build
modern web applications and backend services.
Work with Python, JavaScript, React and SQL.
""",

        "requirements": """
Degree in Computer Science or a related field.
Knowledge of Python and JavaScript.
Knowledge of SQL.
Strong problem-solving skills.
""",

        "salary": "$70,000 - $85,000",

        "application_url": "https://example.com/apply/graduate-software-engineer"
    },

    {
        "title": "Frontend Developer Intern",
        "company": "DigitalWorks",
        "location": "Sydney",
        "industry": "Technology",
        "job_type": "Internship",

        "description": """
Work with our frontend development team to build
responsive and accessible web applications.
You will work with modern frontend technologies.
""",

        "requirements": """
Knowledge of HTML, CSS and JavaScript.
React experience is desirable.
Basic Git knowledge.
Understanding of responsive web design.
""",

        "salary": "$30 per hour",

        "application_url": "https://example.com/apply/frontend-intern"
    },

    {
        "title": "Junior Data Analyst",
        "company": "FinancePro",
        "location": "Melbourne",
        "industry": "Finance",
        "job_type": "Graduate",

        "description": """
Analyse business data and create reports to support
financial and business decision making.
""",

        "requirements": """
SQL knowledge.
Excel knowledge.
Python is preferred.
Strong data analysis and problem-solving skills.
""",

        "salary": "$65,000 - $80,000",

        "application_url": "https://example.com/apply/junior-data-analyst"
    },

    {
        "title": "Cybersecurity Intern",
        "company": "SecureNet",
        "location": "Brisbane",
        "industry": "Technology",
        "job_type": "Internship",

        "description": """
Support the cybersecurity team with security monitoring,
risk assessment and vulnerability management.
""",

        "requirements": """
Currently studying Cybersecurity, Computer Science
or a related degree.
Basic networking knowledge.
Understanding of cybersecurity principles.
Strong analytical skills.
""",

        "salary": "$28 per hour",

        "application_url": "https://example.com/apply/cybersecurity-intern"
    },

    {
        "title": "Junior Web Developer",
        "company": "WebStudio",
        "location": "Melbourne",
        "industry": "Technology",
        "job_type": "Full-time",

        "description": """
Develop and maintain websites and web applications
for a range of clients.
""",

        "requirements": """
HTML, CSS and JavaScript experience.
Knowledge of React or another frontend framework.
Basic understanding of REST APIs.
Git experience.
""",

        "salary": "$60,000 - $75,000",

        "application_url": "https://example.com/apply/junior-web-developer"
    },

    {
        "title": "Graduate Backend Developer",
        "company": "CloudSystems",
        "location": "Sydney",
        "industry": "Technology",
        "job_type": "Graduate",

        "description": """
Join our backend engineering team to develop APIs,
database services and cloud-based applications.
Work with Python, FastAPI, PostgreSQL and AWS.
""",

        "requirements": """
Degree in Computer Science, Software Engineering
or a related field.
Knowledge of Python.
Understanding of REST APIs and databases.
Basic knowledge of Git.
""",

        "salary": "$72,000 - $88,000",

        "application_url": "https://example.com/apply/graduate-backend-developer"
    },

    {
        "title": "Graduate Business Analyst",
        "company": "FinanceStock",
        "location": "Melbourne",
        "industry": "Finance",
        "job_type": "Graduate",

        "description": """
Work with finance and technology teams to analyse
requirements, improve processes and support project delivery.
""",

        "requirements": """
Degree in Business, Information Systems or a related field.
Strong communication skills.
Analytical and problem-solving abilities.
Knowledge of Excel and basic data analysis.
""",

        "salary": "$68,000 - $82,000",

        "application_url": "https://example.com/apply/graduate-business-analyst"
    },

    {
        "title": "IT Support Intern",
        "company": "AusTech Solutions",
        "location": "Brisbane",
        "industry": "Technology",
        "job_type": "Internship",

        "description": """
Assist the IT support team with troubleshooting,
hardware setup, software installation and user support.
""",

        "requirements": """
Currently studying IT, Computer Science or a related degree.
Basic Windows and networking knowledge.
Good communication skills.
Ability to troubleshoot technical problems.
""",

        "salary": "$27 per hour",

        "application_url": "https://example.com/apply/it-support-intern"
    },

    {
        "title": "Junior Python Developer",
        "company": "DataCore",
        "location": "Sydney",
        "industry": "Technology",
        "job_type": "Full-time",

        "description": """
Develop Python applications and data processing tools.
Work with APIs, databases and automated data pipelines.
""",

        "requirements": """
Good knowledge of Python.
Understanding of SQL and relational databases.
Basic REST API knowledge.
Git experience.
Strong problem-solving skills.
""",

        "salary": "$65,000 - $78,000",

        "application_url": "https://example.com/apply/junior-python-developer"
    },

    {
        "title": "Graduate Cloud Engineer",
        "company": "CloudBridge",
        "location": "Perth",
        "industry": "Technology",
        "job_type": "Graduate",

        "description": """
Work with our cloud engineering team to deploy,
monitor and maintain cloud infrastructure and applications.
Gain experience with AWS, Docker and CI/CD pipelines.
""",

        "requirements": """
Degree in Computer Science, IT or Software Engineering.
Basic understanding of cloud computing.
Knowledge of Linux and networking.
Familiarity with Git is desirable.
""",

        "salary": "$75,000 - $90,000",

        "application_url": "https://example.com/apply/graduate-cloud-engineer"
    }
]

# seed database
def seed():

    # Make sure the database and tables exist.
    init_db()

    db = get_db()

    try:

        for job in jobs:

            # Prevent duplicate seed jobs.
            existing = db.execute(
                """
                SELECT id
                FROM jobs
                WHERE title = ?
                AND company = ?
                """,
                (
                    job["title"],
                    job["company"]
                )
            ).fetchone()

            if existing:
                continue

            db.execute(
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
                    job["title"],
                    job["company"],
                    job["location"],
                    job["industry"],
                    job["job_type"],
                    job["description"].strip(),
                    job["requirements"].strip(),
                    job["salary"],
                    job["application_url"]
                )
            )

        db.commit()

        print("Sample jobs successfully added.")

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# run
if __name__ == "__main__":
    seed()
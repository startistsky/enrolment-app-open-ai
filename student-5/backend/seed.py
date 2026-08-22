import os
import sqlite3


# ============================================================
# Database location
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE = os.path.join(
    DATABASE_DIR,
    "career.db"
)


# Make sure database/ exists
os.makedirs(DATABASE_DIR, exist_ok=True)


# ============================================================
# Connect to database
# ============================================================

db = sqlite3.connect(DATABASE)

db.row_factory = sqlite3.Row


# ============================================================
# Create jobs table
# ============================================================

db.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT NOT NULL,

    company TEXT NOT NULL,

    location TEXT,

    industry TEXT,

    job_type TEXT,

    description TEXT,

    requirements TEXT,

    salary TEXT,

    application_url TEXT,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
)
""")


# ============================================================
# Sample jobs
# ============================================================

jobs = [

    (
        "Frontend Developer Intern",
        "GreenTech Solutions",
        "Sydney",
        "Technology",
        "Internship",

        """
        Work with the frontend development team to build
        responsive web applications and improve user experiences.

        You will work with HTML, CSS and JavaScript and gain
        experience working with modern web development practices.
        """,

        """
        Basic knowledge of HTML, CSS and JavaScript.

        Understanding of responsive design.

        Git knowledge is desirable.

        Good communication and problem-solving skills.
        """,

        "$25 per hour",

        "https://example.com/jobs/frontend-intern"
    ),

    (
        "Graduate Software Developer",
        "Future Systems",
        "Melbourne",
        "Technology",
        "Graduate",

        """
        Join our graduate software development program and work
        with experienced developers to build business applications.

        You will participate in software development, testing,
        debugging and code reviews.
        """,

        """
        Degree in Computer Science, Software Engineering
        or a related field.

        Knowledge of Python, Java or JavaScript.

        Understanding of databases and APIs.

        Strong analytical and problem-solving skills.
        """,

        "$65,000 - $75,000",

        "https://example.com/jobs/graduate-developer"
    ),

    (
        "Data Analyst Intern",
        "DataWorks Australia",
        "Sydney",
        "Finance",
        "Internship",

        """
        Support the analytics team by preparing datasets,
        creating reports and identifying useful business insights.

        This is an opportunity to gain practical experience
        working with real business data.
        """,

        """
        Basic SQL knowledge.

        Familiarity with Excel.

        Python or data analysis experience is desirable.

        Strong attention to detail.
        """,

        "$28 per hour",

        "https://example.com/jobs/data-analyst-intern"
    ),

    (
        "Marketing Graduate",
        "Bright Marketing",
        "Brisbane",
        "Marketing",
        "Graduate",

        """
        Work with the marketing team to plan campaigns,
        create digital content and analyse campaign performance.

        You will gain experience across social media,
        content marketing and digital advertising.
        """,

        """
        Degree in Marketing, Business or Communications.

        Strong written communication skills.

        Interest in digital marketing.

        Basic knowledge of social media platforms.
        """,

        "$60,000 - $68,000",

        "https://example.com/jobs/marketing-graduate"
    ),

    (
        "Junior Web Developer",
        "Digital Studio",
        "Sydney",
        "Technology",
        "Full-time",

        """
        Help develop and maintain websites for clients across
        Australia.

        You will work with designers and developers to create
        accessible, responsive and modern websites.
        """,

        """
        HTML and CSS experience.

        JavaScript knowledge.

        Git and GitHub knowledge.

        Understanding of responsive web design.
        """,

        "$70,000 - $80,000",

        "https://example.com/jobs/junior-web-developer"
    ),

    (
        "Software Engineering Intern",
        "CloudCore",
        "Melbourne",
        "Technology",
        "Internship",

        """
        Work alongside software engineers on cloud-based
        applications and internal development projects.

        You will participate in coding, testing and technical
        discussions.
        """,

        """
        Currently studying Computer Science,
        Software Engineering or a related degree.

        Python, JavaScript or Java knowledge.

        Basic understanding of APIs.

        Interest in cloud technologies.
        """,

        "$30 per hour",

        "https://example.com/jobs/software-engineering-intern"
    ),

    (
        "Business Analyst Graduate",
        "Consulting Group Australia",
        "Sydney",
        "Finance",
        "Graduate",

        """
        Assist consultants with business analysis,
        requirements gathering and process improvement projects.

        You will work with clients and technical teams
        to identify business problems and solutions.
        """,

        """
        Degree in Business, Information Systems,
        Commerce or a related field.

        Strong communication skills.

        Analytical thinking.

        Excel knowledge.
        """,

        "$68,000 - $78,000",

        "https://example.com/jobs/business-analyst-graduate"
    ),

    (
        "UX Design Intern",
        "Creative Digital",
        "Brisbane",
        "Technology",
        "Internship",

        """
        Assist the UX team with user research, wireframes,
        prototypes and usability testing.

        You will work closely with developers and product
        managers to improve digital experiences.
        """,

        """
        Studying UX Design, Interaction Design,
        Computer Science or a related field.

        Figma knowledge.

        Understanding of user-centred design.

        Good visual and communication skills.
        """,

        "$26 per hour",

        "https://example.com/jobs/ux-design-intern"
    ),

    (
        "Cyber Security Graduate",
        "SecureNet",
        "Sydney",
        "Technology",
        "Graduate",

        """
        Join our cyber security team and assist with security
        monitoring, vulnerability assessments and incident
        response activities.
        """,

        """
        Degree in Cyber Security, Computer Science
        or Information Technology.

        Understanding of networking.

        Basic security concepts.

        Strong problem-solving skills.
        """,

        "$72,000 - $82,000",

        "https://example.com/jobs/cyber-security-graduate"
    ),

    (
        "Digital Marketing Intern",
        "GrowthHub",
        "Melbourne",
        "Marketing",
        "Internship",

        """
        Help create digital marketing campaigns,
        social media content and email campaigns.

        You will also help analyse campaign performance
        and customer engagement.
        """,

        """
        Studying Marketing, Business or Communications.

        Interest in social media marketing.

        Good writing skills.

        Basic analytics knowledge.
        """,

        "$24 per hour",

        "https://example.com/jobs/digital-marketing-intern"
    )
]


# ============================================================
# Insert jobs
# ============================================================

inserted = 0

for job in jobs:

    # Prevent duplicate jobs
    existing = db.execute(
        """
        SELECT id
        FROM jobs
        WHERE title = ?
        AND company = ?
        """,
        (
            job[0],
            job[1]
        )
    ).fetchone()

    if existing:
        continue

    db.execute(
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
        job
    )

    inserted += 1


# ============================================================
# Save
# ============================================================

db.commit()


# ============================================================
# Show result
# ============================================================

total = db.execute(
    "SELECT COUNT(*) AS count FROM jobs"
).fetchone()["count"]


db.close()


print("========================================")
print(" CareerConnect Database Seeder")
print("========================================")
print(f"Database: {DATABASE}")
print(f"Jobs inserted: {inserted}")
print(f"Total jobs: {total}")
print("========================================")
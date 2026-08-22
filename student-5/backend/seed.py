from database import (
    get_db,
    init_db
)


jobs = [

    {
        "title":
            "Graduate Software Engineer",

        "company":
            "TechNova",

        "location":
            "Sydney",

        "industry":
            "Technology",

        "job_type":
            "Graduate",

        "description":
            """
            Join our software engineering team
            building modern web applications.
            Work with Python, JavaScript,
            React and SQL.
            """,

        "requirements":
            """
            Degree in Computer Science or related field.
            Python and JavaScript knowledge.
            SQL knowledge.
            Strong problem solving skills.
            """,

        "salary":
            "$70,000 - $85,000",

        "application_url":
            "https://example.com"
    },


    {
        "title":
            "Frontend Developer Intern",

        "company":
            "DigitalWorks",

        "location":
            "Sydney",

        "industry":
            "Technology",

        "job_type":
            "Internship",

        "description":
            """
            Work with our frontend development team
            to build responsive web applications.
            """,

        "requirements":
            """
            HTML, CSS and JavaScript.
            React experience is desirable.
            Git knowledge.
            """,

        "salary":
            "$30 per hour",

        "application_url":
            "https://example.com"
    },


    {
        "title":
            "Junior Data Analyst",

        "company":
            "FinancePro",

        "location":
            "Melbourne",

        "industry":
            "Finance",

        "job_type":
            "Graduate",

        "description":
            """
            Analyse business data and create reports
            for financial decision making.
            """,

        "requirements":
            """
            SQL.
            Excel.
            Python preferred.
            Data analysis skills.
            """,

        "salary":
            "$65,000 - $80,000",

        "application_url":
            "https://example.com"
    }

]


def seed():

    init_db()

    db = get_db()


    for job in jobs:

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
                job["description"],
                job["requirements"],
                job["salary"],
                job["application_url"]

            )
        )


    db.commit()

    db.close()


    print(
        "Jobs successfully added."
    )


if __name__ == "__main__":
    seed()
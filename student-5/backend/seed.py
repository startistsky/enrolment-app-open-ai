from database import get_db, init_db


init_db()

db = get_db()


jobs = [
    (
        "Software Engineering Intern",
        "Atlassian",
        "Sydney",
        "Technology",
        "Internship",
        "Work with experienced software engineers to build and improve web applications. You will contribute to real engineering projects and learn modern development practices.",
        "Python, JavaScript, SQL, Git, problem solving and basic software engineering knowledge.",
        "$30 - $35 per hour",
        "https://www.atlassian.com/"
    ),

    (
        "Graduate Software Developer",
        "Canva",
        "Sydney",
        "Technology",
        "Graduate",
        "Join a software engineering team and help build products used by millions of people. You will work with engineers, designers and product teams.",
        "Python or JavaScript, REST APIs, Git, databases and strong problem solving skills.",
        "$75,000 - $85,000",
        "https://www.canva.com/"
    ),

    (
        "Finance Graduate",
        "Commonwealth Bank",
        "Sydney",
        "Finance",
        "Graduate",
        "Join a graduate program focused on financial services, technology and business operations.",
        "Finance, accounting, analytical skills, communication and problem solving.",
        "$70,000 - $80,000",
        "https://www.commbank.com.au/"
    ),

    (
        "Marketing Intern",
        "Adobe",
        "Melbourne",
        "Marketing",
        "Internship",
        "Support marketing campaigns, content creation and digital marketing activities.",
        "Communication, social media, marketing fundamentals and analytical skills.",
        "$28 - $32 per hour",
        "https://www.adobe.com/"
    ),

    (
        "Junior Data Analyst",
        "Deloitte",
        "Brisbane",
        "Technology",
        "Full-time",
        "Analyse business data and create reports that help organisations make better decisions.",
        "SQL, Excel, Python, data visualisation and analytical thinking.",
        "$65,000 - $75,000",
        "https://www.deloitte.com/"
    ),

    (
        "Part-Time IT Support Assistant",
        "Telstra",
        "Melbourne",
        "Technology",
        "Part-time",
        "Provide technical support to staff and assist with troubleshooting hardware and software issues.",
        "IT fundamentals, communication, troubleshooting and customer service.",
        "$30 - $35 per hour",
        "https://www.telstra.com.au/"
    )
]


for job in jobs:

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


db.commit()
db.close()

print("Jobs added successfully!")
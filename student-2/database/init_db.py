import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path


DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parent / "assignments.db"))


def seed_date(days):
    return (date.today() + timedelta(days=days)).isoformat()


def initialise_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    assignments = [
        ("25220967", "Advanced Software Development", "Release 0 Technical Report", "Document the microservices architecture and implementation evidence.", seed_date(9), "High", "In Progress", 45),
        ("25220967", "Advanced Software Development", "Release 0 Demo Video", "Record and edit the integrated team demonstration.", seed_date(8), "High", "Not Started", 10),
        ("25220967", "Data Analytics", "Dashboard Analysis", "Complete charts and explain the main findings.", seed_date(4), "High", "In Progress", 65),
        ("25220967", "Cloud Computing", "AWS Architecture Review", "Review security groups, scaling, and deployment evidence.", seed_date(13), "Medium", "Not Started", 20),
        ("25220967", "Machine Learning", "Model Evaluation Quiz", "Revise precision, recall, validation, and model selection.", seed_date(2), "Medium", "In Progress", 70),
        ("25220967", "Software Development Studio", "Sprint Retrospective", "Summarise sprint outcomes, blockers, and improvements.", seed_date(16), "Low", "Not Started", 0),
        ("25220967", "Advanced Software Development", "Docker Integration", "Validate frontend, backend, database, and Ollama containers.", seed_date(6), "High", "In Progress", 55),
        ("25220967", "Requirements Engineering", "Use Case Narratives", "Complete alternate flows and acceptance criteria.", seed_date(20), "Medium", "Not Started", 15),
        ("25220967", "Data Analytics", "Excel Visualisation", "Format buy and sell points and finalise chart labels.", seed_date(-2), "Medium", "Completed", 100),
        ("25220967", "Professional Practice", "Communication Plan", "Finalise stakeholders, channels, frequency, and ownership.", seed_date(25), "Low", "Completed", 100),
    ]

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DROP TABLE IF EXISTS assignments")
        connection.execute(
            """
            CREATE TABLE assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                assignment_title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
                status TEXT NOT NULL CHECK(status IN ('Not Started', 'In Progress', 'Completed')),
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
                created_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO assignments (
                student_id, subject_name, assignment_title, description,
                due_date, priority, status, progress
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            assignments,
        )
    print(f"Database initialised with {len(assignments)} assignments: {DB_PATH}")


if __name__ == "__main__":
    initialise_database()

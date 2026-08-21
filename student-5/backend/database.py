import sqlite3

DATABASE = "..student-5//database/career.db"

def get_db():
    db = sqlite3.cnnect(DATABASE)
    db.row_factory = sqlite3.Row
    return db 

def init_db():
    db = get_db()
    db.executescript("""
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

        CREATE TABLE IF NOT EXISTS career_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        locations TEXT,
        industries TEXT,
        job_types TEXT,
        skills TEXT,
        career_goals TEXT
    );

    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Interested',
        notes TEXT,
        applied_at TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );
        CREATE TABLE IF NOT EXISTS job_ai_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER UNIQUE NOT NULL,
        skills TEXT,
        qualifications TEXT,
        experience TEXT,
        ats_keywords TEXT,
        summary TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );
    """)

    db.commit()
    db.close()

    

import sqlite3

conn = sqlite3.connect("events.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    emoji TEXT,
    description TEXT
)
""")

events = [
    ("Wellbeing Week 2026", "2026-08-08", "Wellbeing", "Student Centre", "🌿",
     "Drop-in wellbeing activities, peer support and practical ways to recharge during semester."),

    ("Thursday Night Basketball", "2026-08-08", "Sport", "Ross Milbourne Sports Hall", "🏀",
     "Friendly social basketball for students of all skill levels. Bring a friend and join a team."),

    ("Campus Handball Social", "2026-08-09", "Sport", "Sports Centre", "🤾",
     "A beginner-friendly social competition with relaxed rules and plenty of team spirit."),

    ("Discover Sydney Walk", "2026-08-09", "Social", "Central Station", "🌆",
     "Explore hidden gems around Sydney with other students and make new friends."),

    ("AI & Future Careers Workshop", "2026-08-10", "Career", "Building 11", "🤖",
     "Learn how AI is changing graduate jobs and what skills employers are looking for."),

    ("International Student Mixer", "2026-08-10", "Social", "Student Commons", "🌏",
     "Meet students from around the world in a casual evening with games, snacks and music."),

    ("Python for Beginners", "2026-08-11", "Workshop", "Building 10", "💻",
     "A practical beginner session covering Python basics through small coding activities."),

    ("Career Fair 2026", "2026-08-12", "Career", "Great Hall", "💼",
     "Meet employers, ask questions about graduate programs and explore internship opportunities."),

    ("Photography Walk", "2026-08-13", "Creative", "Alumni Green", "📷",
     "Walk around campus and nearby streets while learning simple photography techniques."),

    ("Board Game Night", "2026-08-14", "Social", "Student Lounge", "🎲",
     "A relaxed evening with strategy games, party games and free snacks."),

    ("Sustainability Market", "2026-08-15", "Community", "Alumni Green", "♻️",
     "Browse student stalls, recycled goods, sustainable products and local community initiatives."),

    ("Startup Pitch Night", "2026-08-16", "Career", "Building 11", "🚀",
     "Student founders pitch ideas to a panel and receive practical feedback from industry guests."),

    ("Yoga on the Green", "2026-08-17", "Wellbeing", "Alumni Green", "🧘",
     "A calm morning yoga session suitable for beginners. Mats are available in limited numbers."),

    ("Cybersecurity Challenge", "2026-08-18", "Workshop", "Building 10", "🔐",
     "Solve beginner-friendly cybersecurity puzzles in teams and learn core security concepts."),

    ("Student Club Expo", "2026-08-19", "Community", "Great Hall", "🎪",
     "Discover campus clubs, meet committee members and sign up for activities that interest you."),

    ("Film Night: Student Shorts", "2026-08-20", "Creative", "Theatre Room", "🎬",
     "Watch a selection of short films created by students, followed by a casual discussion.")
]

cursor.execute("SELECT COUNT(*) FROM events")
count = cursor.fetchone()[0]

if count == 0:
    cursor.executemany("""
    INSERT INTO events (
        title,
        date,
        category,
        location,
        emoji,
        description
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, events)

conn.commit()
conn.close()

print("Database created successfully.")
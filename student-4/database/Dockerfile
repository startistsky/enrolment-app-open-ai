FROM python:3.13-slim

WORKDIR /app

COPY student-4/database/init_db.py /app/init_db.py

VOLUME ["/data"]

ENV DATABASE_PATH=/data/events.db

CMD ["python", "init_db.py"]
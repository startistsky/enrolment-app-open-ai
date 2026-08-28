FROM python:3.12-slim

WORKDIR /app

COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/backend/database.py .
COPY student-5/backend/seed.py .

ENV DATABASE_PATH=/data/career.db

RUN mkdir -p /data

CMD ["python", "seed.py"]

#seed when db container starts
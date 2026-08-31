FROM python:3.12-slim

WORKDIR /app

COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/model /data

COPY student-5/backend/model/database.py /app/model/database.py
COPY student-5/backend/model/seed.py /app/seed.py

ENV DATABASE_PATH=/data/career.db

CMD ["python", "seed.py"]

#seed when db container starts
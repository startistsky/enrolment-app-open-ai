FROM python:3.12-slim

WORKDIR /app

COPY student-5/backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/backend/ .

ENV DATABASE_PATH=/data/career.db

EXPOSE 8005

CMD ["python", "app.py"]

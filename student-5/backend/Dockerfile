FROM python:3.12-slim

WORKDIR /app

COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/backend/ .

COPY student-5/frontend/ /frontend/

ENV DATABASE_PATH=/data/career.db

RUN mkdir -p /data

EXPOSE 8005

CMD ["python", "app.py"]

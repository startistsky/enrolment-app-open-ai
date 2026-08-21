FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY student-3/backend/app.py /app/app.py
COPY student-3/database /app/database

EXPOSE 8000

CMD ["python", "app.py"]

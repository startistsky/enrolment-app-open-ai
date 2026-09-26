FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask flask-cors requests

COPY student-3/backend/app.py /app/app.py
COPY student-3/backend/rag_client.py /app/rag_client.py

CMD ["python", "app.py"]
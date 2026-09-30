FROM python:3.12-slim

WORKDIR /app

COPY student-3/backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY student-3/backend/app.py /app/app.py
COPY student-3/backend/rag_client.py /app/rag_client.py
COPY student-3/backend/mcp_client.py /app/mcp_client.py

CMD ["python", "app.py"]

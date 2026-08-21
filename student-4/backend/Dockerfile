FROM python:3.13-slim

WORKDIR /app

COPY student-4/backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY student-4/backend/ .

EXPOSE 8000

CMD ["python", "app.py"]
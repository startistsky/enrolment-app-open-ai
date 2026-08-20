FROM python:3.13-slim

WORKDIR /app/student-4/backend

COPY student-4/backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY student-4/backend/ /app/student-4/backend/
COPY student-4/frontend/ /app/student-4/frontend/
COPY student-4/database/ /app/student-4/database/
COPY shared/frontend/css/ /app/shared/frontend/css/

EXPOSE 8000

CMD ["python", "app.py"]
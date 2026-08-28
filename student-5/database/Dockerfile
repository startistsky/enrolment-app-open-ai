FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend
COPY student-5/backend ./backend
COPY student-5/frontend ./frontend

ENV DATABASE_PATH=/data/career.db

# Flask port
EXPOSE 5005

# Start Flask
CMD ["python", "backend/app.py"]

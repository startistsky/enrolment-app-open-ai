FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend
COPY backend ./backend
COPY frontend ./frontend

# Flask port
EXPOSE 5005

# Start Flask
CMD ["python", "backend/app.py"]
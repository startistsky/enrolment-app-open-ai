FROM python:3.12-slim
WORKDIR /app
COPY student-2/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY student-2/backend/ .
EXPOSE 8002
CMD ["python", "app.py"]

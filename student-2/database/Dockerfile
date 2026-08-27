FROM python:3.12-slim
WORKDIR /app
COPY student-2/database/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY student-2/database/ .
EXPOSE 5002
CMD ["sh", "-c", "test -f \"$DATABASE_PATH\" || python init_db.py; python app.py"]

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY student-3/database/database_api.py /app/database_api.py
COPY student-3/database/campus_resources.db /app/campus_resources.db

EXPOSE 5004

CMD ["python", "database_api.py"]
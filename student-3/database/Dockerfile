FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY student-3/database/init_db.py /app/init_db.py
COPY student-3/database/database_api.py /app/database_api.py

EXPOSE 5004

CMD ["sh", "-c", "python init_db.py && python database_api.py"]
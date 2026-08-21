FROM python:3.13-slim

WORKDIR /app

COPY student-4/database/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY student-4/database/init_db.py /app/init_db.py
COPY student-4/database/app.py /app/app.py
COPY student-4/database/event_controller.py /app/event_controller.py
COPY student-4/database/event_repository.py /app/event_repository.py

ENV DATABASE_PATH=/data/events.db

EXPOSE 5002

CMD ["sh", "-c", "python init_db.py && python app.py"]
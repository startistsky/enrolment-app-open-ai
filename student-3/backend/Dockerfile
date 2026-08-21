FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY student-3/backend/app.py /app/app.py

EXPOSE 8000

CMD ["python", "app.py"]
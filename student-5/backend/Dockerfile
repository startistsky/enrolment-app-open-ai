FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/backend/ .

COPY student-5/frontend/ /frontend/
COPY student-5/backend/nginx-proxy.conf /etc/nginx/conf.d/default.conf

ENV DATABASE_PATH=/data/career.db

RUN mkdir -p /data

EXPOSE 8005
EXPOSE 8006

CMD ["sh", "-c", "nginx && exec python app.py"]

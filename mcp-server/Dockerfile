FROM python:3.12-slim

WORKDIR /app

COPY mcp-server/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/ ./mcp-server/

WORKDIR /app/mcp-server

EXPOSE 9001

CMD ["python", "server.py"]

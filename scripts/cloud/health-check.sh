#!/usr/bin/env bash
# Read-only checks run on the VM. CRUD writes are collected separately as evidence.
set -Eeuo pipefail
for port in 8888 8081 8082 8083 8080 8085; do
  curl --fail --silent --show-error --retry 5 --retry-connrefused "http://127.0.0.1:$port/" >/dev/null
  echo "Frontend $port: reachable"
done
for port in 8001 8002 8003 8000; do
  curl --fail --silent --show-error "http://127.0.0.1:$port/health"
  echo
 done
docker compose -p asd-group5-cloud -f docker-compose.cloud.yml exec -T student5-backend \
  python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8005/health", timeout=5)'
echo 'Backend 8005 (container loopback): healthy'
for endpoint in '8081/api/courses' '8082/api/assignments' '8083/resources' '8080/api/events' '8085/api/jobs'; do
  curl --fail --silent --show-error "http://127.0.0.1:$endpoint" >/dev/null
  echo "Database-backed read $endpoint: reachable"
done
disabled_endpoints=('8001/api/mcp/course-count' '8001/api/rag/course' '8001/api/multi-agent/course-workflow' '8002/api/ai/recommendations' '8003/recommend' '8000/api/ai' '8005/api/ai/chat')
if [[ ! -f docker-compose.bonus.yml ]]; then
  for endpoint in "${disabled_endpoints[@]}"; do
    code=$(curl --silent --show-error -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:$endpoint")
    [[ "$code" == 503 ]] || { echo "Expected disabled 503 from $endpoint, received $code" >&2; exit 1; }
  done
fi
echo 'Health/read checks and deployment-mode AI checks passed. This does not prove CRUD writes or human release approval.'
if [[ -f docker-compose.bonus.yml ]]; then
  compose=(-p asd-group5-cloud -f docker-compose.cloud.yml -f docker-compose.bonus.yml)
  for service in mcp-server rag-server multi-agent-server; do
    docker compose "${compose[@]}" ps --status running --services | grep -Fxq "$service" \
      || { echo "Bonus service is not running: $service" >&2; exit 1; }
    echo "Bonus service $service: running"
  done
  docker compose "${compose[@]}" exec -T mcp-server \
    python -c 'import urllib.request; urllib.request.urlopen("http://student5-backend:8006/health", timeout=5); urllib.request.urlopen("http://student1-backend:8001/health", timeout=5); urllib.request.urlopen("http://student2-backend:8002/health", timeout=5); urllib.request.urlopen("http://backend:8000/health", timeout=5)' \
    || { echo 'MCP cannot reach one or more student backends' >&2; exit 1; }
  echo 'MCP to Student 1, 2, 4, and 5 backends: reachable'
  docker compose "${compose[@]}" exec -T student5-backend \
    python -c 'import json,urllib.request; status=json.load(urllib.request.urlopen("http://127.0.0.1:8005/api/ai/status", timeout=10)); assert status.get("success") and status.get("available"), "Student 5 Ollama integration is unavailable"; assert any(model.startswith(status.get("model", "")) for model in status.get("models", [])), "Configured Student 5 Ollama model is missing"'
  echo 'Student 5 AI/Ollama integration: ready'
fi

#!/usr/bin/env bash
# Read-only checks run on the VM. CRUD writes are collected separately as evidence.
set -Eeuo pipefail
for port in 8888 8081 8082 8083 8080 8085; do
  curl --fail --silent --show-error --retry 5 --retry-connrefused "http://127.0.0.1:$port/" >/dev/null
  echo "Frontend $port: reachable"
done
for port in 8001 8002 8003 8000 8005; do
  curl --fail --silent --show-error "http://127.0.0.1:$port/health"
  echo
 done
for endpoint in '8081/api/courses' '8082/api/assignments' '8083/resources' '8080/api/events' '8085/api/jobs'; do
  curl --fail --silent --show-error "http://127.0.0.1:$endpoint" >/dev/null
  echo "Database-backed read $endpoint: reachable"
done
for endpoint in '8001/api/mcp/course-count' '8001/api/rag/course' '8001/api/multi-agent/course-workflow' '8002/api/ai/recommendations' '8003/recommend' '8000/api/ai' '8005/api/ai/chat'; do
  code=$(curl --silent --show-error -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:$endpoint")
  [[ "$code" == 503 ]] || { echo "Expected disabled 503 from $endpoint, received $code" >&2; exit 1; }
done
echo 'Health/read checks and AI-disabled checks passed. This does not prove CRUD writes or human release approval.'

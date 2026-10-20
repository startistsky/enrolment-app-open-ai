#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL=${BASE_URL:-http://127.0.0.1:8003}

python3 - "$BASE_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base_url = sys.argv[1].rstrip("/")


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def request_json(path, payload=None, timeout=180):
    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"{path} returned HTTP {error.code}"
        ) from error

    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"{path} returned an invalid response")

    return body


print("===== Student 3 Backend =====", flush=True)
health = request_json("/health", timeout=15)
check(health.get("status") == "ok", "Bonus response validation failed")
print("PASS: Backend Health", flush=True)

print("===== B2 MCP =====", flush=True)
mcp = request_json("/api/mcp/resource-count", timeout=30)
check(mcp.get("mode") == "mcp", "Bonus response validation failed")
check(mcp.get("tool") == "resource_count", "Bonus response validation failed")
check(isinstance(mcp.get("result"), dict), "Bonus response validation failed")
print("PASS: B2 MCP", flush=True)

print("===== B1 Ollama =====", flush=True)
ai = request_json(
    "/recommend",
    {"question": "Recommend a campus computer lab for studying."},
    timeout=120,
)
check(isinstance(ai.get("recommendation"), str), "Bonus response validation failed")
check(ai["recommendation"].strip(), "Bonus response validation failed")
check(ai.get("model") == "qwen2.5:0.5b", "Bonus response validation failed")
print("PASS: B1 Ollama Recommendation", flush=True)

print("===== B3 RAG =====", flush=True)
rag = request_json(
    "/rag/recommend",
    {"question": "What computer labs are available on campus?"},
    timeout=120,
)
check(rag.get("mode") == "rag", "Bonus response validation failed")
check(isinstance(rag.get("answer"), str), "Bonus response validation failed")
check(rag["answer"].strip(), "Bonus response validation failed")
check(isinstance(rag.get("citations"), list), "Bonus response validation failed")
check(rag.get("confidence") in {"high", "medium"}, "Bonus response validation failed")
check(rag["citations"], "Bonus response validation failed")
print("PASS: B3 RAG Grounded Retrieval", flush=True)

print("===== B4 Multi-Agent =====", flush=True)
workflow = request_json(
    "/api/multi-agent/resource",
    {"question": "Review available campus computer labs."},
    timeout=240,
)
check(isinstance(workflow.get("workflow_id"), str), "Bonus response validation failed")
check(workflow.get("status") == "pending_human_review", "Bonus response validation failed")
review = workflow.get("human_review", {})
check(review.get("required") is True, "Bonus response validation failed")
check(review.get("status") == "pending", "Bonus response validation failed")
print("PASS: B4 Multi-Agent Human Review", flush=True)

print("GROUP5_STUDENT3_BONUS_HEALTH_PASSED", flush=True)
PY

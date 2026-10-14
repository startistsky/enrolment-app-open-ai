import json
import os
from pathlib import Path

import requests


class ModelError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def generate(role, context, required_fields, prompt_name=None):
    """Request a deterministic JSON object; never substitute invented output."""
    model = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b") if role == "reviewer" else "qwen2.5:0.5b"
    prompt_file = prompt_name or role
    instruction = (
        Path(__file__).parent / "prompts" / f"{prompt_file}_prompt.txt"
    ).read_text(encoding="utf-8")
    json_types = {
        str: "string", list: "array", dict: "object",
        bool: "boolean", int: "integer", float: "number",
    }
    schema = {
        "type": "object",
        "properties": {
            key: {"type": json_types[kind], **({"items": {}} if kind is list else {})}
            for key, kind in required_fields.items()
        },
        "required": list(required_fields),
        "additionalProperties": False,
    }
    try:
        response = requests.post(
            os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
            json={"model": model, "system": instruction,
                  "prompt": json.dumps(context, ensure_ascii=False),
                  "stream": False, "format": schema,
                  "options": {"temperature": 0, "seed": 42}},
            timeout=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
        )
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise ModelError("Ollama unavailable or timed out", 503) from exc
    except requests.RequestException as exc:
        raise ModelError("Ollama request failed") from exc
    if not response.ok:
        raise ModelError(f"Ollama returned HTTP {response.status_code}")
    try:
        body = response.json()
        result = json.loads(body["response"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ModelError("Ollama returned invalid JSON output") from exc
    if not isinstance(result, dict) or any(
        not isinstance(result.get(key), kind) for key, kind in required_fields.items()
    ):
        raise ModelError(f"Invalid {role} output structure")
    return {key: result[key] for key in required_fields}

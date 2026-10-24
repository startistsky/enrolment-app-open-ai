import json
import os
from pathlib import Path

import requests


MAX_OUTPUT_ATTEMPTS = 2
RESOURCE_PROMPTS = frozenset({
    "resource_planner",
    "resource_worker",
    "resource_reviewer",
})
RESOURCE_MAX_PREDICT = 256


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
    payload = {
        "model": model,
        "system": instruction,
        "prompt": json.dumps(context, ensure_ascii=False),
        "stream": False,
        "format": schema,
    }
    last_error = "invalid JSON output"
    completion_metadata = {}

    for attempt in range(MAX_OUTPUT_ATTEMPTS):
        options = {"temperature": 0, "seed": 42 + attempt}
        if prompt_file in RESOURCE_PROMPTS:
            options["num_predict"] = RESOURCE_MAX_PREDICT
        attempt_payload = {
            **payload,
            "options": options,
        }
        completion_metadata = {}
        try:
            response = requests.post(
                os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
                json=attempt_payload,
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
            completion_metadata = {
                key: body.get(key)
                for key in ("done_reason", "eval_count", "prompt_eval_count")
            } if isinstance(body, dict) else {}
            output = body["response"]
            result = json.loads(output)
        except (ValueError, KeyError, TypeError) as exc:
            last_error = "invalid JSON output"
            parse_error = exc
        else:
            if isinstance(result, dict) and not any(
                not isinstance(result.get(key), kind)
                for key, kind in required_fields.items()
            ):
                return {key: result[key] for key in required_fields}
            last_error = f"invalid {role} output structure"
            parse_error = None

        if attempt == MAX_OUTPUT_ATTEMPTS - 1:
            metadata = ", ".join(
                f"{key}={value}" for key, value in completion_metadata.items()
            )
            detail = f"; last completion: {metadata}" if metadata else ""
            error = ModelError(
                f"Ollama returned {last_error} after {MAX_OUTPUT_ATTEMPTS} attempts{detail}"
            )
            if parse_error is not None:
                raise error from parse_error
            raise error

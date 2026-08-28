import os


AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://ollama:11434/api/generate"
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "qwen2.5:0.5b"
)

AI_TIMEOUT = int(
    os.getenv("AI_TIMEOUT", "60")
)
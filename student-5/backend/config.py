import os

from dotenv import load_dotenv


# Load .env from project root
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(ENV_FILE)


# ==========================================
# Flask
# ==========================================

FLASK_HOST = os.getenv(
    "FLASK_HOST",
    "127.0.0.1"
)

FLASK_PORT = int(
    os.getenv(
        "FLASK_PORT",
        "5005"
    )
)


# ==========================================
# Ollama
# ==========================================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.1:8b"
)

OLLAMA_FAST_MODEL = os.getenv(
    "OLLAMA_FAST_MODEL",
    "qwen2.5:0.5b"
)


# ==========================================
# Database
# ==========================================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "../database/career.db"
)

if not os.path.isabs(DATABASE_PATH):

    DATABASE_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            DATABASE_PATH
        )
    )


# ==========================================
# Agent
# ==========================================

AGENT_NAME = (
    "Career and Internship Agent"
)

AGENT_MAX_ITERATIONS = 3

AGENT_MAX_JOBS = 10

AGENT_MIN_MATCH_SCORE = 50
"""Django settings. Every value that varies per environment is read from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- Django core -------------------------------------------------------------------------------

SECRET_KEY = env_str("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    host.strip()
    for host in env_str("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
    "ingestion",
    "conversation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "rag"),
        "USER": env_str("POSTGRES_USER", "rag"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "rag"),
        "HOST": env_str("POSTGRES_HOST", "localhost"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = env_str("TIME_ZONE", "UTC")
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# --- Application settings ----------------------------------------------------------------------

REDIS_URL = env_str("REDIS_URL", "redis://localhost:6379/0")

QDRANT_URL = env_str("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = env_str("QDRANT_API_KEY")
QDRANT_COLLECTION = env_str("QDRANT_COLLECTION", "document_chunks")

# --- Model Provider (Ollama local / OpenAI fallback) ------------------------------------
OLLAMA_BASE_URL = env_str("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_API_KEY = env_str("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env_str("ANTHROPIC_API_KEY")

EMBEDDING_MODEL = env_str("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIMENSIONS = env_int("EMBEDDING_DIMENSIONS", 768)
EMBEDDING_BATCH_SIZE = env_int("EMBEDDING_BATCH_SIZE", 64)

CHAT_MODEL = env_str("CHAT_MODEL", "llama3.2")
CHAT_MAX_TOKENS = env_int("CHAT_MAX_TOKENS", 1024)
LLM_TIMEOUT_SECONDS = env_int("LLM_TIMEOUT_SECONDS", 120)

UPLOAD_MAX_BYTES = env_int("UPLOAD_MAX_BYTES", 20 * 1024 * 1024)
CHUNK_SIZE = env_int("CHUNK_SIZE", 1000)
CHUNK_OVERLAP = env_int("CHUNK_OVERLAP", 200)

RAG_TOP_K = env_int("RAG_TOP_K", 5)
CHAT_MEMORY_MAX_MESSAGES = env_int("CHAT_MEMORY_MAX_MESSAGES", 20)
CHAT_MEMORY_TTL_SECONDS = env_int("CHAT_MEMORY_TTL_SECONDS", 86400)

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Any OpenAI-compatible endpoint: Groq (default), a local llama.cpp / Ollama server, ...
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    parse_model: str = "openai/gpt-oss-20b"
    narrate_model: str = "openai/gpt-oss-120b"
    guard_model: str = "meta-llama/llama-prompt-guard-2-86m"
    guard_threshold: float = 0.5
    llm_timeout: float = 30.0

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'pantry_chef.db').as_posix()}"
    admin_token: str = "change-me-admin"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

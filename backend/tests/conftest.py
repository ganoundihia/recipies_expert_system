import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine.reasoner import ExpertSystem
from app.kb.loader import load_seed_kb
from app.kb.matcher import IngredientMatcher
from app.main import create_app


class FakeLLM:
    """Scripted stand-in for the OpenAI-compatible client; records every call."""

    def __init__(self, handler: Callable[[str, list[dict], bool], str]) -> None:
        self.handler = handler
        self.calls: list[tuple[str, list[dict]]] = []

    def chat(self, model, messages, *, json_mode=False, temperature=0.2, max_tokens=None):
        self.calls.append((model, messages))
        return self.handler(model, messages, json_mode)

    def chat_json(self, model, messages, **kwargs):
        return json.loads(self.chat(model, messages, json_mode=True, **kwargs))


@pytest.fixture(scope="session")
def kb():
    return load_seed_kb()


@pytest.fixture(scope="session")
def expert(kb):
    return ExpertSystem(kb)


@pytest.fixture(scope="session")
def matcher(kb):
    return IngredientMatcher(kb)


def make_settings(tmp_path, **overrides) -> Settings:
    return Settings(_env_file=None, llm_api_key="", database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}", admin_token="secret", **overrides)


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as client:
        yield client

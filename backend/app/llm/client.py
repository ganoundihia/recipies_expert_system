"""Minimal client for OpenAI-compatible chat APIs (Groq, llama.cpp server, Ollama, ...)."""

from __future__ import annotations

import json
import logging
import time
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class ChatModel(Protocol):
    def chat(self, model: str, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.2, max_tokens: int | None = None) -> str: ...

    def chat_json(self, model: str, messages: list[dict], **kwargs) -> dict: ...


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0, max_retries: int = 4) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.waited_s = 0.0  # Total time spent backing off on rate limits, so benchmarks can report it separately.
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)

    def chat(self, model: str, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.2, max_tokens: int | None = None) -> str:
        payload: dict = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        for attempt in range(self.max_retries + 1):
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.HTTPError as error:
                if attempt == self.max_retries:
                    raise LLMError(f"LLM request failed: {error}") from error
                self._wait(2**attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.max_retries:
                    raise LLMError(f"LLM unavailable ({response.status_code})")
                delay = _retry_after(response, attempt)
                log.warning("LLM %s returned %s, retrying in %.1fs", model, response.status_code, delay)
                self._wait(delay)
                continue
            if response.status_code >= 400:
                raise LLMError(f"LLM error {response.status_code}: {response.text[:300]}")
            choice = response.json()["choices"][0]
            if choice.get("finish_reason") == "length":
                raise LLMError("LLM output was truncated")
            return choice["message"]["content"] or ""
        raise LLMError("unreachable")

    def _wait(self, seconds: float) -> None:
        self.waited_s += seconds
        time.sleep(seconds)

    def chat_json(self, model: str, messages: list[dict], **kwargs) -> dict:
        content = self.chat(model, messages, json_mode=True, **kwargs)
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMError(f"Model returned invalid JSON: {content[:200]}") from error


def _retry_after(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("retry-after")
    try:
        return min(float(header), 60.0) if header else float(2 ** (attempt + 1))
    except ValueError:
        return float(2 ** (attempt + 1))

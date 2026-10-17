"""Prompt-injection screening with Llama Prompt Guard 2 before any text reaches the parsing LLM."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.llm.client import ChatModel, LLMError

log = logging.getLogger(__name__)


class GuardResult(BaseModel):
    checked: bool
    score: float = 0.0
    flagged: bool = False


def screen(client: ChatModel | None, model: str, text: str, threshold: float) -> GuardResult:
    if client is None:
        return GuardResult(checked=False)
    try:
        score = float(client.chat(model, [{"role": "user", "content": text}], temperature=0).strip())
    except (LLMError, ValueError) as error:
        log.warning("Prompt guard unavailable: %s", error)
        return GuardResult(checked=False)
    return GuardResult(checked=True, score=round(score, 4), flagged=score >= threshold)

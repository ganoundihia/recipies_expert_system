"""Translates recipe steps (authored in English) on demand; results are cached by the caller."""

from __future__ import annotations

from app.llm.client import ChatModel, LLMError
from app.llm.narrator import LANGUAGE_NAMES
from app.llm.parser import dumps_compact

PROMPT = """Translate these baking instructions into {language}. Keep every number, temperature and duration exactly.
Return JSON: {{"steps": [ ...one translated string per input step, same order... ]}}"""


def translate_steps(client: ChatModel, model: str, steps: list[str], lang: str) -> list[str] | None:
    try:
        data = client.chat_json(model, [{"role": "system", "content": PROMPT.format(language=LANGUAGE_NAMES[lang])}, {"role": "user", "content": dumps_compact(steps)}], temperature=0)
    except LLMError:
        return None
    translated = data.get("steps")
    if not isinstance(translated, list) or len(translated) != len(steps) or not all(isinstance(s, str) and s.strip() for s in translated):
        return None
    return translated

"""PantryChef: the hybrid pipeline (guard -> parse -> expert system -> grounded narration)."""

from __future__ import annotations

import logging
import time

from app.config import Settings
from app.engine.reasoner import ExpertSystem
from app.kb.matcher import IngredientMatcher
from app.kb.models import KnowledgeBase
from app.llm.client import ChatModel, LLMError, OpenAICompatibleClient
from app.llm.fallback_parser import parse_keywords
from app.llm.guard import screen
from app.llm.narrator import narrate
from app.llm.parser import parse_with_llm
from app.schemas import AskRequest, UserRequest

log = logging.getLogger(__name__)


class PantryChef:
    def __init__(self, kb: KnowledgeBase, settings: Settings, client: ChatModel | None = None) -> None:
        self.settings = settings
        if client is None and settings.llm_api_key:
            client = OpenAICompatibleClient(settings.llm_base_url, settings.llm_api_key, settings.llm_timeout)
        self.client = client
        self.load(kb)

    def load(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.expert = ExpertSystem(kb)
        self.matcher = IngredientMatcher(kb)

    @property
    def llm_enabled(self) -> bool:
        return self.client is not None

    def _merge_safety_constraints(self, llm: UserRequest, keywords: UserRequest) -> tuple[UserRequest, list[str]]:
        """Safety first: diets and allergies found by the deterministic parser are always applied.

        The LLM may miss or mistranslate a constraint (e.g. Darija words for sesame or peanuts);
        a missed allergy must never depend on a model, so both parsers' constraints are unioned.
        """
        added = [f"diet:{d}" for d in keywords.diets if d not in llm.diets] + [f"avoid:{a}" for a in keywords.avoid if a not in llm.avoid]
        if not added:
            return llm, []
        avoid = sorted({*llm.avoid, *keywords.avoid})
        pantry = [p for p in llm.pantry if not set(avoid) & set(self.kb.ingredients[p.id].allergens)]
        merged = llm.model_copy(update={"diets": sorted({*llm.diets, *keywords.diets}), "avoid": avoid, "pantry": pantry})
        log.info("Safety net added constraints the LLM missed: %s", added)
        return merged, added

    def ask(self, ask: AskRequest) -> dict:
        timings: dict[str, float] = {}
        started = time.perf_counter()

        def lap(stage: str, since: float) -> float:
            now = time.perf_counter()
            timings[stage] = round((now - since) * 1000)
            return now

        guard = screen(self.client, self.settings.guard_model, ask.text, self.settings.guard_threshold)
        mark = lap("guard", started)

        parser = "keywords"
        unrecognized: list[str] = []
        safety_net: list[str] = []
        if self.client is not None and not guard.flagged:
            try:
                request, unrecognized = parse_with_llm(self.client, self.settings.parse_model, ask.text, self.matcher)
                request, safety_net = self._merge_safety_constraints(request, parse_keywords(ask.text, self.matcher))
                parser = "llm"
            except LLMError as error:
                log.warning("LLM parsing failed, falling back to keywords: %s", error)
                request = parse_keywords(ask.text, self.matcher)
        else:
            request = parse_keywords(ask.text, self.matcher)
        request = request.model_copy(update={"top_k": ask.top_k, **({"lang": ask.lang} if ask.lang else {})})
        mark = lap("parse", mark)

        result = self.expert.recommend(request)
        mark = lap("reasoning", mark)

        narration = narrate(None if guard.flagged else self.client, self.settings.narrate_model, result, self.expert, self.matcher, request)
        lap("narration", mark)
        timings["total"] = round((time.perf_counter() - started) * 1000)

        return {
            "request": request.model_dump(),
            "parser": parser,
            "unrecognized": unrecognized,
            "safety_net": safety_net,
            "guard": guard.model_dump(),
            "answer": narration.model_dump(),
            "result": result.model_dump(),
            "timings_ms": timings,
        }
